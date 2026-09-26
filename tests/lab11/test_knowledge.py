import asyncio

import pytest
pytest.importorskip("fastapi")
import knowledge


@pytest.fixture
def notes(tmp_path):
    root = tmp_path / "Memory"
    (root / "Technical" / "AWS").mkdir(parents=True)
    (root / "Technical" / "AWS" / "Networking.md").write_text("# Networking\nVPC peering is not transitive.\n")
    (root / "Personal").mkdir()
    (root / "Personal" / "Health.md").write_text("Private.\n")
    (root / ".archive").mkdir()
    (root / ".archive" / "Old.md").write_text("Stale.\n")
    (root / "README.md").write_text("About this folder.\n")
    return root


def test_reads_nested_files_and_skips_hidden_folders(notes):
    sections = knowledge.load_sections(notes)
    files = {i.split("#")[0] for i in sections}
    assert files == {"Technical/AWS/Networking.md", "Personal/Health.md", "README.md"}


def test_the_include_list_keeps_only_those_folders(notes):
    sections = knowledge.load_sections(notes, folders=["Technical"])
    assert {i.split("#")[0] for i in sections} == {"Technical/AWS/Networking.md"}


def test_each_section_says_where_it_came_from(notes):
    (text,) = knowledge.load_sections(notes, folders=["Technical"]).values()
    assert text.startswith("Technical/AWS/Networking.md › Networking") and "not transitive" in text


def test_long_files_are_split_at_headings_and_by_size(tmp_path):
    long = "# Intro\nShort intro.\n## Details\n" + "\n\n".join(f"Paragraph {i}. " + "x" * 400 for i in range(10))
    (tmp_path / "Guide.md").write_text(long)
    sections = knowledge.load_sections(tmp_path)
    assert len(sections) > 3
    assert all(len(t) <= knowledge.MAX_CHARS + 120 for t in sections.values())  # + the "path › heading" prefix
    assert any("› Intro" in t for t in sections.values()) and any("› Details" in t for t in sections.values())


def test_the_store_is_read_only(notes, tmp_path):
    store = knowledge.KnowledgeStore(notes, cache=tmp_path / "kb.json", on_search=lambda *a: None)
    assert store.writable is False
    with pytest.raises(PermissionError):
        asyncio.run(store.add("anything"))


def test_search_reranks_with_system1_and_caches_outside_the_folder(notes, tmp_path):
    seen = []
    relevance = lambda query, sections: {i: (0.9 if "VPC" in t else 0.1) for i, t in sections.items()}
    store = knowledge.KnowledgeStore(notes, cache=tmp_path / "kb.json", on_search=lambda *a: seen.append(a),
                                     relevance=relevance, embed=lambda texts: None)
    found = asyncio.run(store.search("Is VPC peering transitive?"))
    assert [e.metadata["path"] for e in found] == ["kb:Technical/AWS/Networking.md#0"]
    assert seen and seen[-1][0] == ["kb:Technical/AWS/Networking.md#0"]
    assert not any(p.name.endswith(".json") for p in notes.rglob("*"))  # nothing written into the folder

import asyncio
import pytest
pytest.importorskip("fastapi")
import memory


def test_watched_store_reports_retrieved_paths(tmp_path):
    seen = []
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda ids, *rest: seen.append(ids), extract=False)
    asyncio.run(store.add("User home\nThe user lives in Dubai."))
    asyncio.run(store.search("Where does the user live? Dubai"))
    assert seen and seen[-1][0].endswith(".md")


def test_graph_links_similar_notes(tmp_path):
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    (tmp_path / "trip.md").write_text("Trip from Dubai to Istanbul in March.")
    (tmp_path / "food.md").write_text("Likes spicy food.")
    g = memory.graph(tmp_path, embed=None)  # fallback: shared capitalised words
    assert {n["id"] for n in g["nodes"]} == {"home.md", "trip.md", "food.md"}
    assert {tuple(sorted((l["source"], l["target"]))) for l in g["links"]} == {("home.md", "trip.md")}


def test_graph_empty_folder(tmp_path):
    assert memory.graph(tmp_path, embed=None) == {"nodes": [], "links": []}


def test_graph_uses_embeddings_when_available(tmp_path):
    (tmp_path / "a.md").write_text("beaches")
    (tmp_path / "b.md").write_text("sand")
    (tmp_path / "c.md").write_text("taxes")
    vectors = {"beaches": [1, 0], "sand": [0.9, 0.1], "taxes": [0, 1]}
    g = memory.graph(tmp_path, embed=lambda texts: [vectors[t] for t in texts])
    assert [tuple(sorted((l["source"], l["target"]))) for l in g["links"]] == [("a.md", "b.md")]


def test_hits_are_counted_and_shown_on_nodes(tmp_path):
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    memory.record_hits(tmp_path, ["home.md"]); memory.record_hits(tmp_path, ["home.md"])
    assert memory.graph(tmp_path, embed=None)["nodes"][0]["hits"] == 2


def test_recall_keeps_only_relevant_notes_best_first(tmp_path):
    seen = []
    relevance = lambda query, notes: {k: (0.95 if "Syed" in v else 0.1) for k, v in notes.items()}
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda *a: seen.append(a), extract=False, relevance=relevance)
    asyncio.run(store.add("Name\nThe user's name is Syed."))
    asyncio.run(store.add("Home\nThe user lives in Dubai."))
    found = asyncio.run(store.search("What's my name?"))
    assert [e.metadata["path"] for e in found] == ["name.md"]
    ids, texts, scores, query = seen[-1]
    assert ids == ["name.md"] and scores == [0.95] and query == "What's my name?"


def test_an_unrelated_question_recalls_nothing(tmp_path):
    seen = []
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda *a: seen.append(a), extract=False,
                             relevance=lambda query, notes: {k: 0.05 for k in notes})
    asyncio.run(store.add("Home\nThe user lives in Dubai."))
    assert asyncio.run(store.search("What's the capital of Peru?")) == []
    assert seen == []


def test_saving_a_note_is_reported(tmp_path):
    stored = []
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda *a: None, extract=False, on_store=stored.append)
    asyncio.run(store.add("Home\nThe user lives in Dubai."))
    assert stored == ["home.md"]


def test_graph_lists_newest_notes_first(tmp_path):
    import os, time
    (tmp_path / "a-old.md").write_text("Old fact."); (tmp_path / "z-new.md").write_text("New fact.")
    os.utime(tmp_path / "a-old.md", (time.time() - 100, time.time() - 100))
    assert [n["id"] for n in memory.graph(tmp_path, embed=None)["nodes"]] == ["z-new.md", "a-old.md"]


def test_forget_deletes_the_note_and_its_hits(tmp_path):
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    memory.record_hits(tmp_path, ["home.md"])
    memory.forget(tmp_path, "home.md")
    assert memory.graph(tmp_path, embed=None) == {"nodes": [], "links": []}
    import pytest as _p
    with _p.raises(ValueError):
        memory.forget(tmp_path, "../chats/x.json")  # only notes in the memory folder

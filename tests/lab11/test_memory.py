import asyncio
import pytest
pytest.importorskip("fastapi")
import memory


def test_watched_store_reports_retrieved_paths(tmp_path):
    seen = []
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda ids, texts: seen.append(ids), extract=False)
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

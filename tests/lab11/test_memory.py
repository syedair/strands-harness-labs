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


def test_notes_recalled_together_wire_together(tmp_path):
    (tmp_path / "food.md").write_text("Likes spicy food.")
    (tmp_path / "home.md").write_text("Lives near the sea.")
    (tmp_path / "name.md").write_text("Is called Syed.")
    memory.record_hits(tmp_path, ["food.md", "home.md"])
    memory.record_hits(tmp_path, ["home.md", "food.md"])
    links = memory.graph(tmp_path, embed=None)["links"]
    assert links == [{"source": "food.md", "target": "home.md", "weight": 0.0, "together": 2}]


def test_similar_notes_link_even_before_firing_together(tmp_path):
    (tmp_path / "a.md").write_text("beaches")
    (tmp_path / "b.md").write_text("sand")
    vectors = {"beaches": [1, 0], "sand": [0.9, 0.1]}
    links = memory.graph(tmp_path, embed=lambda texts: [vectors[t] for t in texts])["links"]
    assert links[0]["together"] == 0 and links[0]["weight"] > 0.6


def test_recalled_notes_carry_when_they_were_saved(tmp_path):
    import os
    relevance = lambda query, notes: {k: 0.9 for k in notes}
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda *a: None, extract=False, relevance=relevance)
    (tmp_path / "old.md").write_text("The user's name is Syed.")
    (tmp_path / "new.md").write_text("The user's name is John.")
    os.utime(tmp_path / "old.md", (1790000000, 1790000000))
    os.utime(tmp_path / "new.md", (1790100000, 1790100000))
    found = asyncio.run(store.search("What's my name?"))
    assert found[0].metadata["path"] == "new.md"  # on a tie, the newer note comes first
    assert found[0].content.startswith("(saved 2026-")
    assert "The user's name is John." in found[0].content


def test_a_retry_after_feedback_still_recalls_for_the_users_question(tmp_path):
    # Injected memories last one model call; the retry's search sees the check's feedback as the
    # latest "user" message, so it must search with the user's real question again.
    calls = []
    store = memory.store_for("ollama/gpt-oss:20b", tmp_path, on_search=lambda *a: None, extract=False,
                             relevance=lambda q, n: calls.append(q) or {k: 0.9 for k in n})
    (tmp_path / "name.md").write_text("The user's name is John.")
    asyncio.run(store.search("What's my name?"))
    retry = asyncio.run(store.search("[system1-completion-check] Your answer skipped part of the request."))
    assert [e.metadata["path"] for e in retry] == ["name.md"]
    assert calls == ["What's my name?", "What's my name?"]


def test_forget_about_deletes_only_the_notes_on_that_topic(tmp_path):
    (tmp_path / "name.md").write_text("The user's name is John.")
    (tmp_path / "name-2.md").write_text("Users name is John.")
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    judge = lambda about, notes: {i: 0.9 if "John" in t else 0.1 for i, t in notes.items()}
    assert sorted(memory.forget_about(tmp_path, "my name", judge)) == ["name-2.md", "name.md"]
    assert [p.name for p in tmp_path.glob("*.md")] == ["home.md"]


def test_forget_about_nothing_matching_deletes_nothing(tmp_path):
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    assert memory.forget_about(tmp_path, "my name", lambda about, notes: {i: 0.2 for i in notes}) == []
    assert (tmp_path / "home.md").exists()


def test_notes_that_name_the_topic_are_forgotten_without_asking_system1(tmp_path):
    (tmp_path / "trip.md").write_text("User is planning a trip to Istanbul.")
    (tmp_path / "plug.md").write_text("Electrical outlets in istanbul are Type C/F.")
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    unsure = lambda about, notes: {i: 0.2 for i in notes}  # a weak classifier that misses them
    assert sorted(memory.forget_about(tmp_path, "Istanbul", unsure)) == ["plug.md", "trip.md"]
    assert (tmp_path / "home.md").exists()


def test_common_words_in_the_topic_dont_match_every_note(tmp_path):
    (tmp_path / "home.md").write_text("The user lives in Dubai.")
    assert memory.forget_about(tmp_path, "the user's trip", lambda about, notes: {i: 0.1 for i in notes}) == []

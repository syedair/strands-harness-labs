import pytest
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

import app as server  # noqa: E402
import chats  # noqa: E402
import knowledge  # noqa: E402

no_model = lambda texts: None  # noqa: E731  (indexing without an embedding model still counts sections)


@pytest.fixture
def vault(tmp_path):
    root = tmp_path / "Vault"
    (root / "Trips").mkdir(parents=True)
    (root / "Trips" / "Lisbon.md").write_text("# Lisbon\nTram 28 is packed by 10am.\n")
    (root / ".obsidian").mkdir()
    (root / ".obsidian" / "workspace.md").write_text("editor state\n")
    return root


def test_adding_a_folder_indexes_it(tmp_path, vault):
    bases = knowledge.Bases(tmp_path / "data")
    base = bases.add(str(vault), embed=no_model)
    assert base["files"] == 1 and base["sections"] == 1 and base["indexed_at"]
    assert bases.list() == [base]


@pytest.mark.parametrize("path, reason", [("/no/such/folder", "doesn't exist"), ("__file__", "isn't a folder"),
                                          ("__empty__", "no markdown")])
def test_bad_folders_are_refused_with_a_reason(tmp_path, path, reason):
    (tmp_path / "empty").mkdir()
    (tmp_path / "file.md").write_text("x")
    path = {"__file__": str(tmp_path / "file.md"), "__empty__": str(tmp_path / "empty")}.get(path, path)
    with pytest.raises(ValueError, match=reason):
        knowledge.Bases(tmp_path / "data").add(path, embed=no_model)


def test_a_huge_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(knowledge, "MAX_FILES", 2)
    for i in range(3):
        (tmp_path / f"n{i}.md").write_text("x")
    with pytest.raises(ValueError, match="more than 2"):
        knowledge.Bases(tmp_path / "data").add(str(tmp_path), embed=no_model)


def test_removing_a_base_drops_its_index_but_never_the_folder(tmp_path, vault):
    bases = knowledge.Bases(tmp_path / "data")
    base = bases.add(str(vault), embed=lambda texts: [[1.0, 0.0]] * len(texts))
    assert bases.cache(base["id"]).exists()
    bases.remove(base["id"])
    assert bases.list() == [] and not bases.cache(base["id"]).exists() and (vault / "Trips" / "Lisbon.md").exists()


def test_knowledge_bases_come_only_from_settings(tmp_path, vault, monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_DIR", str(vault))  # an old .env line does nothing now
    assert knowledge.Bases(tmp_path / "data", embed=no_model).list() == []


def test_each_base_is_its_own_read_only_store(tmp_path, vault):
    bases = knowledge.Bases(tmp_path / "data")
    base = bases.add(str(vault), embed=no_model)
    (store,) = bases.stores(on_search=lambda *a: None)
    assert store.writable is False and store.name == f"knowledge-{base['id']}" and store.root == vault


@pytest.fixture
def client(monkeypatch, tmp_path):
    server.AGENTS.clear()
    monkeypatch.setattr(server, "STORE", chats.ChatStore(tmp_path / "data"))
    monkeypatch.setattr(server, "DATA", tmp_path / "data")
    monkeypatch.setattr(knowledge.memory, "ollama_embed", no_model)
    return TestClient(server.app)


def test_settings_routes_add_list_reindex_and_remove(client, vault):
    server.AGENTS["abc"] = ("agent", "turn", "key")
    added = client.post("/api/knowledge", json={"path": str(vault)}).json()
    assert added["sections"] == 1 and server.AGENTS == {}  # chats pick the new base up on their next message
    assert [b["id"] for b in client.get("/api/knowledge").json()] == [added["id"]]
    assert client.post(f"/api/knowledge/{added['id']}/index").json()["sections"] == 1
    assert client.post("/api/knowledge", json={"path": "/no/such"}).status_code == 400
    assert client.delete(f"/api/knowledge/{added['id']}").json() == {"ok": True}
    assert client.get("/api/knowledge").json() == []


def test_the_graph_shows_every_base(client, vault):
    client.post("/api/knowledge", json={"path": str(vault)})
    g = client.get("/api/memory").json()
    assert [n["id"] for n in g["nodes"] if n.get("kind") == "knowledge"][0].startswith("kb:")
    assert g["knowledge"]["sections"] == 1

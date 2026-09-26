import io
import zipfile

import pytest
pytest.importorskip("fastapi")
import skills

SKILL = "---\nname: visa-check\ndescription: Check visa rules for a trip.\n---\nSteps…\n"


def zipped(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, text in files.items():
            z.writestr(name, text)
    return buffer.getvalue()


def test_a_skill_md_is_installed_in_its_own_folder(tmp_path):
    assert skills.install(tmp_path, "SKILL.md", SKILL.encode()) == "visa-check"
    assert (tmp_path / "visa-check" / "SKILL.md").read_text() == SKILL


def test_a_zipped_folder_keeps_its_references_and_scripts(tmp_path):
    data = zipped({"visa-check/SKILL.md": SKILL, "visa-check/references/rules.md": "EU rules", "visa-check/scripts/x.py": "print()"})
    assert skills.install(tmp_path, "visa-check.zip", data) == "visa-check"
    assert (tmp_path / "visa-check" / "references" / "rules.md").read_text() == "EU rules"
    assert (tmp_path / "visa-check" / "scripts" / "x.py").exists()


def test_a_zip_with_skill_md_at_the_top_works_too(tmp_path):
    assert skills.install(tmp_path, "s.zip", zipped({"SKILL.md": SKILL, "notes.md": "x"})) == "visa-check"
    assert (tmp_path / "visa-check" / "notes.md").exists()


@pytest.mark.parametrize("name, data, reason", [
    ("SKILL.md", b"no frontmatter", "name"),
    ("SKILL.md", b"---\nname: Bad Name!\ndescription: x\n---\n", "name"),
    ("SKILL.md", b"---\nname: ok\n---\n", "description"),
    ("s.zip", zipped({"readme.md": "x"}), "SKILL.md"),
    ("s.zip", zipped({"SKILL.md": SKILL, "../escape.md": "x"}), "path"),
    ("s.zip", b"not a zip", "zip"),
    ("skill.txt", b"x", "SKILL.md or a .zip"),
])
def test_bad_uploads_are_refused_with_a_reason(tmp_path, name, data, reason):
    with pytest.raises(ValueError, match=reason):
        skills.install(tmp_path, name, data)
    assert not (tmp_path.parent / "escape.md").exists()


def test_an_existing_skill_is_not_overwritten(tmp_path):
    skills.install(tmp_path, "SKILL.md", SKILL.encode())
    with pytest.raises(ValueError, match="already"):
        skills.install(tmp_path, "SKILL.md", SKILL.replace("Steps", "Other").encode())
    assert "Steps" in (tmp_path / "visa-check" / "SKILL.md").read_text()


def test_uploading_a_skill_lists_it_and_rebuilds_chat_agents(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import app as server
    monkeypatch.setattr(server, "SKILLS", tmp_path)
    server.AGENTS["abc"] = ("agent", "turn", "key")
    client = TestClient(server.app)
    response = client.post("/api/skills", files={"file": ("SKILL.md", SKILL.encode())})
    assert response.json() == {"name": "visa-check"} and server.AGENTS == {}
    assert [s["name"] for s in server.read_skills()] == ["visa-check"]
    refused = client.post("/api/skills", files={"file": ("SKILL.md", SKILL.encode())})
    assert refused.status_code == 400 and "already" in refused.json()["detail"]

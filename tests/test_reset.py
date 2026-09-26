import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_reset_clears_state_and_keeps_skills(tmp_path):
    shutil.copy(REPO / "reset.sh", tmp_path / "reset.sh")
    for folder in (".agent/sessions/travel", ".agent/memory", "trips", ".agent/skills/packing-list"):
        (tmp_path / folder).mkdir(parents=True)
    (tmp_path / ".agent/skills/packing-list/SKILL.md").write_text("skill")

    # Run from somewhere else: the script must clean its own folder, not the cwd.
    subprocess.run(["bash", str(tmp_path / "reset.sh")], cwd="/", check=True)

    assert not (tmp_path / ".agent/sessions").exists()
    assert not (tmp_path / ".agent/memory").exists()
    assert not (tmp_path / "trips").exists()
    assert (tmp_path / ".agent/skills/packing-list/SKILL.md").exists()

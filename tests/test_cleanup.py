import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

FAKE_OLLAMA = """#!/usr/bin/env bash
if [ "$1" = list ]; then
  echo "NAME ID SIZE MODIFIED"
  echo "qwen3.5:4b 2a65 3.4 GB 1h"
  echo "llama3.2:latest a80c 2.0 GB 1y"
else echo "ollama $*" >> "$LOG"; fi
"""
FAKE_UVX = """#!/usr/bin/env bash
if [ "$6" = ls ]; then
  echo "id size last_accessed"
  echo "model/jaredpalmer/kev-4b 159.7M now"
  echo "model/openai/whisper 1G now"
else echo "hf ${*:4}" >> "$LOG"; fi
"""


def run_cleanup(tmp_path, answers):
    for name in ("cleanup.sh",):
        shutil.copy(REPO / name, tmp_path / name)
    (tmp_path / "kev.sh").write_text("echo kev stopped\n")
    (tmp_path / "reset.sh").write_text("echo reset\n")
    (tmp_path / ".venv").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, body in (("ollama", FAKE_OLLAMA), ("uvx", FAKE_UVX)):
        (bin_dir / name).write_text(body)
        (bin_dir / name).chmod(0o755)
    log = tmp_path / "log"
    log.touch()
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "LOG": str(log)}
    subprocess.run(["bash", str(tmp_path / "cleanup.sh")], input=answers, text=True,
                   env=env, check=True, capture_output=True)
    return log.read_text(), (tmp_path / ".venv").exists()


def test_nothing_is_deleted_without_a_yes(tmp_path):
    deleted, venv_kept = run_cleanup(tmp_path, "\n\n\n")
    assert deleted == ""
    assert venv_kept


def test_each_yes_deletes_only_lab_models(tmp_path):
    deleted, venv_kept = run_cleanup(tmp_path, "y\ny\ny\n")
    assert "ollama rm qwen3.5:4b" in deleted
    assert "hf cache rm model/jaredpalmer/kev-4b --yes" in deleted
    assert "llama3.2" not in deleted and "whisper" not in deleted  # not ours: never offered
    assert not venv_kept

# Lab 11: add a skill from the app. A skill is a folder: SKILL.md (name + description up top) plus optional
# references/, scripts/ and assets/. Upload the SKILL.md alone, or the folder as a .zip.
import io
import re
import zipfile
from pathlib import Path, PurePosixPath

NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
MAX_FILES, MAX_BYTES = 200, 10 * 1024 * 1024  # unzipped


def front_matter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    return {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in block.splitlines() if ":" in line)}


def check(text: str) -> str:
    """The skill's name, if its SKILL.md is valid."""
    fields = front_matter(text)
    name = fields.get("name", "")
    if not NAME.fullmatch(name):
        raise ValueError("SKILL.md needs a name: lowercase letters, digits and dashes (e.g. visa-check)")
    if not fields.get("description"):
        raise ValueError("SKILL.md needs a description: when should the agent use this skill?")
    return name


def install(skills_dir: Path, filename: str, data: bytes) -> str:
    """Install an uploaded skill under skills_dir/<name>/ and return its name."""
    if filename.lower().endswith(".md"):
        files = {"SKILL.md": data}
    elif filename.lower().endswith(".zip"):
        files = unzip(data)
    else:
        raise ValueError("Upload a SKILL.md or a .zip of the skill folder")
    if "SKILL.md" not in files:
        raise ValueError("The zip has no SKILL.md (at the top, or inside one folder)")
    name = check(files["SKILL.md"].decode("utf-8", errors="replace"))
    target = Path(skills_dir) / name
    if target.exists():
        raise ValueError(f"A skill called {name} is already installed")
    for relative, content in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return name


def unzip(data: bytes) -> dict[str, bytes]:
    """The zip's files, relative to the folder holding SKILL.md. Refuses paths that climb out."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("That isn't a valid zip file")
    entries = [e for e in archive.infolist() if not e.is_dir() and not e.filename.startswith("__MACOSX/")]
    if len(entries) > MAX_FILES or sum(e.file_size for e in entries) > MAX_BYTES:
        raise ValueError(f"A skill can have up to {MAX_FILES} files and 10 MB")
    for e in entries:
        parts = PurePosixPath(e.filename).parts
        if e.filename.startswith("/") or ".." in parts or "\\" in e.filename:
            raise ValueError(f"Unsafe path in the zip: {e.filename}")
    tops = {PurePosixPath(e.filename).parts[0] for e in entries}
    prefix = f"{tops.pop()}/" if len(tops) == 1 and not any(e.filename == "SKILL.md" for e in entries) else ""
    return {e.filename[len(prefix):]: archive.read(e) for e in entries if e.filename.startswith(prefix)}

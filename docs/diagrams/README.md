# Diagrams

Hand-drawn Excalidraw diagrams for the videos: an intro (what a harness is, Strands, the landscape, System 1, the lab
map) and one per lab. Open any `.excalidraw` file at [excalidraw.com](https://excalidraw.com) (File → Open) or in the
Excalidraw app, VS Code or Obsidian, and edit freely. The `.png` next to each is a rendered preview.

Every number on them comes from a real run of the labs (September 2026) or a source printed on the diagram.

## Rebuild

`make_diagrams.py` builds all of them with the
[excalidraw-diagrams skill](https://github.com/syedair/syedair-skills/tree/main/excalidraw-diagrams), which also
checks the layout. With the skill in `~/.claude/skills/excalidraw-diagrams` (or `EXCALIDRAW_DIAGRAMS` pointing at it),
from the repo root:

```bash
uv run --with fonttools --with brotli --with playwright python docs/diagrams/make_diagrams.py
uv run --with playwright python ~/.claude/skills/excalidraw-diagrams/scripts/render.py docs/diagrams/*.excalidraw
```

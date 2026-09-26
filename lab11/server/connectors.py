# Lab 11: MCP connectors. Each one is an MCP server the harness starts and whose tools the agent can use.
import json
import uuid
from pathlib import Path

PRESETS = {
    "aws-docs": {
        "label": "AWS Documentation",
        "description": "Search and read the AWS docs",
        "config": {"command": "uvx", "args": ["awslabs.aws-documentation-mcp-server@latest"],
                   "env": {"FASTMCP_LOG_LEVEL": "ERROR"}},
    },
    "files": {
        "label": "Chat files",
        "description": "Browse the files attached to this chat",
        "config": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "{chat_dir}"]},
    },
}


def load_custom(data: Path) -> dict:
    path = data / "connectors.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save_custom(data: Path, label: str, command: str, args: list[str]) -> str:
    custom = load_custom(data)
    connector_id = f"custom-{uuid.uuid4().hex[:6]}"
    custom[connector_id] = {"label": label, "description": f"{command} {' '.join(args)}",
                            "config": {"command": command, "args": args}}
    data.mkdir(parents=True, exist_ok=True)
    (data / "connectors.json").write_text(json.dumps(custom, indent=2))
    return connector_id


def listing(data: Path) -> list[dict]:
    presets = [{"id": k, "label": v["label"], "description": v["description"], "custom": False} for k, v in PRESETS.items()]
    custom = [{"id": k, "label": v["label"], "description": v["description"], "custom": True}
              for k, v in load_custom(data).items()]
    return presets + custom


def mcp_config(enabled: list[str], chat_dir: Path, custom: dict) -> dict:
    """The standard mcpServers shape the harness takes as mcp_servers=."""
    known = {**PRESETS, **custom}
    config = {}
    for connector_id in enabled:
        if connector_id in known:
            server = json.loads(json.dumps(known[connector_id]["config"]))  # a copy we can fill in
            server["args"] = [str(chat_dir) if a == "{chat_dir}" else a for a in server.get("args", [])]
            config[connector_id] = server
    return config

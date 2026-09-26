import { describe, expect, it } from "vitest";
import { connectorRows } from "./connectors";

const listing = [
  { id: "aws-docs", label: "AWS documentation", description: "", custom: false },
  { id: "files", label: "Chat files", description: "", custom: false },
  { id: "broken", label: "Broken", description: "", custom: true },
];

describe("connectorRows", () => {
  it("lists every connector, whether it's on, its tools, and why it failed", () => {
    const rows = connectorRows(listing, {
      tools: ["web_fetch", "aws-docs_search", "aws-docs_read"],
      connectors: { enabled: ["aws-docs", "broken"], errors: [{ id: "broken", error: "command not found" }] },
    });
    expect(rows.map((r) => [r.id, r.state])).toEqual([["aws-docs", "on"], ["files", "off"], ["broken", "failed"]]);
    expect(rows[0].tools).toEqual(["search", "read"]);
    expect(rows[2].error).toBe("command not found");
  });
});

describe("a connector being switched", () => {
  it("shows the state it's going to, as starting or stopping, until the harness is rebuilt", () => {
    const harness = { tools: [], connectors: { enabled: ["files"], errors: [] } };
    const starting = connectorRows(listing, harness, { id: "aws-docs", on: true });
    expect(starting[0].state).toBe("starting");
    const stopping = connectorRows(listing, harness, { id: "files", on: false });
    expect(stopping[1].state).toBe("stopping");
  });
});

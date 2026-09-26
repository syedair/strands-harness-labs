// What the Connectors tab shows: every connector the app knows, and what it's doing in this chat.
import type { Connector, Harness } from "./api";

export type ConnectorRow = Connector & { state: "on" | "off" | "failed"; tools: string[]; error?: string };

export function connectorRows(listing: Connector[], harness: Pick<Harness, "tools" | "connectors">): ConnectorRow[] {
  return listing.map((c) => {
    const error = harness.connectors.errors.find((e) => e.id === c.id)?.error;
    const on = harness.connectors.enabled.includes(c.id);
    const tools = harness.tools.filter((t) => t.startsWith(`${c.id}_`)).map((t) => t.slice(c.id.length + 1));
    return { ...c, state: error ? "failed" : on ? "on" : "off", tools, error };
  });
}

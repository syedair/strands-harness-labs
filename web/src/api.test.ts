import { describe, expect, it } from "vitest";
import { readEvents } from "./api";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

describe("readEvents", () => {
  it("joins a JSON line split across chunks", async () => {
    const events = [];
    for await (const e of readEvents(streamOf(['{"type":"te', 'xt","delta":"hi"}\n{"type":"done"}\n']))) events.push(e);
    expect(events).toEqual([{ type: "text", delta: "hi" }, { type: "done" }]);
  });

  it("reads a last line without a trailing newline", async () => {
    const events = [];
    for await (const e of readEvents(streamOf(['{"type":"done"}']))) events.push(e);
    expect(events).toEqual([{ type: "done" }]);
  });
});

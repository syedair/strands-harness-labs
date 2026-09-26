import { describe, expect, it } from "vitest";
import { baseSummary } from "./knowledge";

const base = { id: "memory-1", path: "~/Memory", folders: null, files: 44, sections: 522, embedded: true, indexed_at: 0 };

describe("baseSummary", () => {
  it("says how big the base is and when it was indexed", () => {
    expect(baseSummary(base, 30_000)).toBe("44 files · 522 sections · indexed just now");
    expect(baseSummary(base, 3 * 60_000)).toBe("44 files · 522 sections · indexed 3 min ago");
    expect(baseSummary(base, 5 * 3_600_000)).toBe("44 files · 522 sections · indexed 5 h ago");
  });

  it("warns when there was no embedding model to index with", () => {
    expect(baseSummary({ ...base, files: 1, sections: 1, embedded: false }, 0))
      .toBe("1 file · 1 section · indexed just now · not embedded (ollama pull nomic-embed-text)");
  });
});

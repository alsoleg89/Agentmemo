import { describe, it, expect } from "vitest";
import { dedupCandidates } from "../src/reader_extraction.js";

describe("dedupCandidates", () => {
  it("removes case-duplicates, first occurrence wins", () => {
    const result = dedupCandidates(["Apple", "apple", "APPLE"]);
    expect(result).toHaveLength(1);
    expect(result[0]).toBe("Apple");
  });

  it("strips common list prefixes", () => {
    const result = dedupCandidates(["- Running", "1. Pottery", "• Hiking", "2) Camping"]);
    expect(result).toEqual(["Running", "Pottery", "Hiking", "Camping"]);
  });

  it("filters blank lines and whitespace-only entries", () => {
    const result = dedupCandidates(["", "   ", "Running", "  "]);
    expect(result).toEqual(["Running"]);
  });

  it("preserves distinct items in order", () => {
    const result = dedupCandidates(["Running", "Pottery", "Hiking"]);
    expect(result).toEqual(["Running", "Pottery", "Hiking"]);
  });

  it("treats same text with different punctuation as duplicate", () => {
    // "Oliver (cat)" and "oliver cat" both normalise to key "olivercat"
    const result = dedupCandidates(["Oliver (cat)", "oliver cat", "Luna"]);
    expect(result).toHaveLength(2);
    expect(result[0]).toBe("Oliver (cat)");
    expect(result[1]).toBe("Luna");
  });

  it("returns empty array for all-blank input", () => {
    expect(dedupCandidates(["", " ", "\t"])).toEqual([]);
  });
});

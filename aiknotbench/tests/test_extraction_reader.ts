import { describe, it, expect } from "vitest";
import { dedupCandidates, isEnumerationQuestion } from "../src/reader_extraction.js";

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

describe("isEnumerationQuestion", () => {
  it("accepts list-noun questions", () => {
    expect(isEnumerationQuestion("What hobbies does Melanie have?")).toBe(true);
    expect(isEnumerationQuestion("What activities does Melanie do on family hikes?")).toBe(true);
    expect(isEnumerationQuestion("What are the names of Melanie's pets?")).toBe(true);
    expect(isEnumerationQuestion("What events has Caroline participated in?")).toBe(true);
    expect(isEnumerationQuestion("What subjects does Melanie paint?")).toBe(true);
  });

  it("accepts how-many and list/name imperatives", () => {
    expect(isEnumerationQuestion("How many books has Caroline read?")).toBe(true);
    expect(isEnumerationQuestion("List all activities Melanie enjoys.")).toBe(true);
    expect(isEnumerationQuestion("What are Caroline's interests?")).toBe(true);
  });

  it("rejects temporal and causal questions", () => {
    expect(isEnumerationQuestion("When did Caroline go to the support group?")).toBe(false);
    expect(isEnumerationQuestion("How did Melanie feel after the accident?")).toBe(false);
    expect(isEnumerationQuestion("Why did Caroline start volunteering?")).toBe(false);
    expect(isEnumerationQuestion("Who was Melanie's mentor?")).toBe(false);
    expect(isEnumerationQuestion("Did Caroline attend the pride parade?")).toBe(false);
    expect(isEnumerationQuestion("Was Melanie happy about the adoption?")).toBe(false);
  });

  it("rejects single-answer what-questions", () => {
    expect(isEnumerationQuestion("What type of adoption was Caroline researching?")).toBe(false);
    expect(isEnumerationQuestion("What does Melanie do to destress?")).toBe(false);
  });
});

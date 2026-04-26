import { describe, it, expect } from "vitest";
import {
  computeDiagnosticsRecord,
  computeSummary,
  type DiagnosticsRecord,
} from "../scripts/diagnose_recall.js";

// ---- Synthetic entry fixtures -----------------------------------------------

function makeEntry(
  overrides: Partial<{
    conv_idx: number;
    qa_idx: number;
    category: number;
    query: string;
    stage1_bm25: string[];
    stage1_rare: string[];
    stage1_hop: string[];
    pack: string[];
    lexical_bridge: Record<string, unknown> | undefined;
  }> = {},
) {
  const o = {
    conv_idx: 0,
    qa_idx: 0,
    category: 1,
    query: "When did Alice go to the park?",
    stage1_bm25: ["f1", "f2", "f3"],
    stage1_rare: [],
    stage1_hop: [],
    pack: ["f1", "f2"],
    lexical_bridge: undefined,
    ...overrides,
  };

  return {
    run_id: "test-run",
    conv_idx: o.conv_idx,
    qa_idx: o.qa_idx,
    category: o.category,
    query: o.query,
    stage1_candidates: {
      from_bm25: o.stage1_bm25,
      from_rare_tokens: o.stage1_rare,
      from_entity_hop: o.stage1_hop,
    },
    pack_fact_ids: o.pack,
    stage0_lexical_bridge: o.lexical_bridge,
  };
}

// ---- Tests ------------------------------------------------------------------

describe("computeDiagnosticsRecord — PoolGoldRecall@K", () => {
  it("1.0 when all gold IDs are in stage1 pool", () => {
    const entry = makeEntry({ stage1_bm25: ["f1", "f2", "f3"] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      { "D1:1": ["f1"], "D1:2": ["f2"] },
      ["D1:1", "D1:2"],
      "CORRECT",
    );
    expect(rec.pool_gold_recall).toBe(1.0);
  });

  it("0.5 when half of gold IDs are in pool", () => {
    const entry = makeEntry({
      stage1_bm25: ["f1", "f3"],
      pack: ["f1"],
    });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      {},
      ["D1:1", "D1:2"],
      "WRONG",
    );
    expect(rec.pool_gold_recall).toBeCloseTo(0.5);
  });

  it("0.0 when no gold IDs are in pool", () => {
    const entry = makeEntry({
      stage1_bm25: ["f99", "f100"],
      pack: [],
    });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      {},
      ["D1:1", "D1:2"],
      "WRONG",
    );
    expect(rec.pool_gold_recall).toBe(0);
  });

  it("null when no gold IDs provided", () => {
    const entry = makeEntry();
    const rec = computeDiagnosticsRecord(entry, [], {}, [], "WRONG");
    expect(rec.pool_gold_recall).toBeNull();
  });
});

describe("computeDiagnosticsRecord — PackGoldRecall@Budget", () => {
  it("1.0 when all gold in pack", () => {
    const entry = makeEntry({ pack: ["f1", "f2", "f3"] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      {},
      ["D1:1", "D1:2"],
      "CORRECT",
    );
    expect(rec.pack_gold_recall).toBe(1.0);
  });

  it("0 when pack is empty", () => {
    const entry = makeEntry({ pack: [] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1"],
      {},
      ["D1:1"],
      "WRONG",
    );
    expect(rec.pack_gold_recall).toBe(0);
  });
});

describe("computeDiagnosticsRecord — DistractorDensity", () => {
  it("0.5 when half of pack is non-gold", () => {
    const entry = makeEntry({ pack: ["f1", "f99"] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1"],
      {},
      ["D1:1"],
      "CORRECT",
    );
    expect(rec.distractor_density).toBeCloseTo(0.5);
  });

  it("0.0 when all pack facts are gold", () => {
    const entry = makeEntry({ pack: ["f1", "f2"] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      {},
      [],
      "CORRECT",
    );
    expect(rec.distractor_density).toBe(0.0);
  });
});

describe("computeDiagnosticsRecord — ReaderFailDespiteGold", () => {
  it("true when PackGoldRecall=1.0 and verdict=WRONG", () => {
    const entry = makeEntry({ pack: ["f1", "f2"] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      {},
      [],
      "WRONG",
    );
    expect(rec.reader_fail_despite_gold).toBe(true);
    expect(rec.bucket).toBe("LLM-fail");
  });

  it("false when verdict=CORRECT even with full gold in pack", () => {
    const entry = makeEntry({ pack: ["f1", "f2"] });
    const rec = computeDiagnosticsRecord(
      entry,
      ["f1", "f2"],
      {},
      [],
      "CORRECT",
    );
    expect(rec.reader_fail_despite_gold).toBe(false);
  });
});

describe("computeDiagnosticsRecord — bucket classification", () => {
  it("LLM-fail: PackGoldRecall=1.0, verdict=WRONG", () => {
    const entry = makeEntry({ pack: ["f1", "f2"] });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2"], {}, [], "WRONG");
    expect(rec.bucket).toBe("LLM-fail");
  });

  it("partial-recall: PackGoldRecall=0.5, verdict=WRONG", () => {
    const entry = makeEntry({ pack: ["f1", "f99"] });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2"], {}, [], "WRONG");
    expect(rec.bucket).toBe("partial-recall");
  });

  it("low-recall: PackGoldRecall=0.1, verdict=WRONG", () => {
    const entry = makeEntry({ pack: ["f1", "f99", "f100", "f101", "f102", "f103", "f104", "f105", "f106", "f107"] });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10"], {}, [], "WRONG");
    expect(rec.bucket).toBe("low-recall");
  });

  it("hard-miss: PackGoldRecall=0, verdict=WRONG", () => {
    const entry = makeEntry({ pack: ["f99"] });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, [], "WRONG");
    expect(rec.bucket).toBe("hard-miss");
  });

  it("correct: verdict=CORRECT regardless of pack", () => {
    const entry = makeEntry({ pack: [] });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, [], "CORRECT");
    expect(rec.bucket).toBe("correct");
  });
});

describe("computeDiagnosticsRecord — LexicalExpansionUplift", () => {
  it("null by default (Phase A only computes this via A0.lexical)", () => {
    const entry = makeEntry({
      lexical_bridge: { expanded_terms: ["park", "walk"] },
    });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, [], "WRONG");
    expect(rec.lexical_expansion_uplift).toBeNull();
  });
});

describe("computeDiagnosticsRecord — PackPositionEntropy (A0.pack)", () => {
  it("null when pack is empty", () => {
    const entry = makeEntry({ pack: [], stage1_bm25: ["f1"] });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, ["D1:1"], "WRONG");
    expect(rec.pack_position_entropy).toBeNull();
  });

  it("null when no gold in pack", () => {
    const entry = makeEntry({ pack: ["f99", "f100"], stage1_bm25: ["f1", "f99", "f100"] });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, ["D1:1"], "WRONG");
    expect(rec.pack_position_entropy).toBeNull();
  });

  it("0 entropy when all gold concentrated in one third", () => {
    // Pack of 9 facts, gold all in head (positions 0-2)
    const pack = ["f1", "f2", "f3", "x1", "x2", "x3", "x4", "x5", "x6"];
    const entry = makeEntry({ pack, stage1_bm25: pack });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2", "f3"], {}, [], "WRONG");
    // All 3 gold in head → bins=[3,0,0] → H=0
    expect(rec.pack_position_entropy).toBe(0);
  });

  it("positive entropy when gold spread across thirds", () => {
    // Pack of 9 facts, gold in head + tail
    const pack = ["f1", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "f2"];
    const entry = makeEntry({ pack, stage1_bm25: pack });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2"], {}, [], "WRONG");
    // f1 at pos 0 (head), f2 at pos 8 (tail) → bins=[1,0,1] → H > 0
    expect(rec.pack_position_entropy).toBeGreaterThan(0);
  });
});

describe("computeDiagnosticsRecord — LostInMiddleSignal (A0.pack)", () => {
  it("null when pack is empty", () => {
    const entry = makeEntry({ pack: [], stage1_bm25: ["f1"] });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, ["D1:1"], "WRONG");
    expect(rec.lost_in_middle_signal).toBeNull();
  });

  it("0.0 when gold at head only (position 0 in 8-pack)", () => {
    // Pack of 8 facts, middle = positions 2-5 (floor(8*0.25)=2, ceil(8*0.75)=6)
    const pack = ["f1", "x1", "x2", "x3", "x4", "x5", "x6", "x7"];
    const entry = makeEntry({ pack, stage1_bm25: pack });
    const rec = computeDiagnosticsRecord(entry, ["f1"], {}, [], "WRONG");
    // f1 at pos 0: not in [2, 6) → signal = 0
    expect(rec.lost_in_middle_signal).toBe(0);
  });

  it("1.0 when all gold in middle 50%", () => {
    // Pack of 8 facts, middle = [2, 6), gold at positions 2,3,4,5
    const pack = ["x1", "x2", "f1", "f2", "f3", "f4", "x3", "x4"];
    const entry = makeEntry({ pack, stage1_bm25: pack });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2", "f3", "f4"], {}, [], "WRONG");
    expect(rec.lost_in_middle_signal).toBe(1.0);
  });

  it("0.5 when half gold in middle", () => {
    // Pack of 4 facts: gold at positions 0 (head) and 1 (middle for 4-pack)
    // midStart=floor(4*0.25)=1, midEnd=ceil(4*0.75)=3 → middle=[1,3)
    const pack = ["f1", "f2", "x1", "x2"];
    const entry = makeEntry({ pack, stage1_bm25: pack });
    const rec = computeDiagnosticsRecord(entry, ["f1", "f2"], {}, [], "WRONG");
    // f1 at pos 0: not in [1,3); f2 at pos 1: in [1,3) → 1/2 = 0.5
    expect(rec.lost_in_middle_signal).toBeCloseTo(0.5);
  });
});

describe("computeSummary", () => {
  it("correctly counts LLM-fail bucket for cat1", () => {
    const records: DiagnosticsRecord[] = [
      {
        run_id: "r",
        conv_id: "conv0",
        qa_idx: 0,
        category: 1,
        query: "q",
        gold_evidence: [],
        gold_fact_ids: ["f1"],
        gold_fact_ids_per_evidence: {},
        raw_gold_exists: true,
        pool_gold_recall: 1.0,
        pack_gold_recall: 1.0,
        gold_pack_position_median: 0,
        distractor_density: 0.5,
        reader_fail_despite_gold: true,
        lexical_expansion_uplift: null,
        pack_position_entropy: 0.0,
        lost_in_middle_signal: 0.0,
        answer_verdict: "WRONG",
        bucket: "LLM-fail",
      },
      {
        run_id: "r",
        conv_id: "conv0",
        qa_idx: 1,
        category: 1,
        query: "q2",
        gold_evidence: [],
        gold_fact_ids: [],
        gold_fact_ids_per_evidence: {},
        raw_gold_exists: false,
        pool_gold_recall: 0,
        pack_gold_recall: 0,
        gold_pack_position_median: null,
        distractor_density: 1.0,
        reader_fail_despite_gold: false,
        lexical_expansion_uplift: null,
        pack_position_entropy: null,
        lost_in_middle_signal: null,
        answer_verdict: "WRONG",
        bucket: "hard-miss",
      },
    ];

    const summary = computeSummary("r", records);
    expect(summary.buckets["LLM-fail"]).toBe(1);
    expect(summary.buckets["hard-miss"]).toBe(1);
    expect(summary.reader_fail_despite_gold_count).toBe(1);
    expect(summary.by_category["1"]?.buckets["LLM-fail"]).toBe(1);
    expect(summary.by_category["1"]?.buckets["hard-miss"]).toBe(1);
  });
});

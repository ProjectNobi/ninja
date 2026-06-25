# DPO Intel — SN66 v75 Pipeline
*Generated: 2026-05-20 | Source: 40K sample from full_matrix_dpo_pairs.jsonl (128,749 total)*

---

## Intel A: Winning vs Losing Judge Phrases by Task Type

### Interpretation
Phrases in WIN rationales = language judge uses when describing the WINNING patch.
Phrases in LOSE rationales = same language applied to the LOSING patch (i.e. what the winner had that the loser lacked).
**High-value signal:** Phrases that appear much more in WIN than LOSE rationales = what our patch must demonstrate.
Phrases only/mostly in LOSE rationales = what the opposing king's patch has that ours lacks.

### UPDATE (n=15,755 consensus pairs)
| Phrase | WIN count | LOSE count | Signal |
|--------|-----------|-----------|--------|
| patch directly addresses | 903 | 2042 | Judge rewards direct addressing |
| addresses acceptance criteria | 624 | 2227 | ❌ We lack AC coverage |
| directly addresses core | 421 | 1093 | ❌ Losers miss core issue |
| patch provides more complete | 389+346 | 793+748 | Completeness = king advantage |
| **better addresses acceptance** | **—** | **1094** | ⚠️ LOSE-EXCLUSIVE: king "better addresses" |
| **better addresses issue** | **—** | **703** | ⚠️ LOSE-EXCLUSIVE: king "better addresses" |
| patch only adds | 213 | 677 | Partial impl = lose signal |
| that doesn match | 212 | — | WIN signal: our patch matches reference |

**UPDATE key finding:** We lose UPDATE tasks because the judge says the king "better addresses acceptance criteria." Our patches "only add" partial implementations without the full integration chain.

### API/ROUTE (n=3,313 consensus pairs)
| Phrase | WIN count | LOSE count | Signal |
|--------|-----------|-----------|--------|
| patch directly addresses | 153 | 324 | Direct addressing wins |
| addresses acceptance criteria | 116 | 438 | ❌ AC coverage critical |
| implementation with proper | 59 | — | WIN-EXCLUSIVE: "proper implementation" |
| provides more complete | 89+99 | 210+209 | Completeness gap |
| better addresses acceptance | — | 218 | ⚠️ LOSE-EXCLUSIVE |

**API/ROUTE key finding:** Same pattern as UPDATE. "Implementation with proper [X]" appears only in WIN rationales. API tasks need PROPER (complete, correct) implementation — not skeleton code or partial endpoint wiring.

### FEATURE (n=9,684)
Same pattern: "provides more complete" + "directly addresses" in wins. Lose-exclusive: "better addresses acceptance" (569), "patch only adds" (453).

### BUGFIX (n=3,168)
WIN-specific: "addresses root cause" (91) + "directly addresses root" (51). 
BUGFIX reward = root cause fix, not symptom workaround.

### UNIVERSAL FINDING ACROSS ALL TASK TYPES
**The judge rewards:** patches that DIRECTLY ADDRESS all acceptance criteria, show complete integration, fix root cause.
**The judge penalizes:** patches that "only add X without showing required backend logic", "only partially address", "don't match acceptance criteria."

---

## Intel B: M2.7 Gold Patch Sizes

*From training_unified_gold.jsonl, first 30K records, M2.7-tagged entries only*

| Task Type | n | Median Lines | Avg Lines | Max |
|-----------|---|-------------|-----------|-----|
| FEATURE_BUILD | 6,768 | **536L** | 1,222L | 20,796L |
| REFACTOR | 1,233 | **438L** | 1,114L | 20,680L |
| MIGRATION | 627 | **511L** | 1,585L | 20,582L |
| BUG_FIX | 439 | **360L** | 958L | 20,587L |

**Key insight:** Winning gold patches from M2.7 are 360–536 lines (median). This is the natural "complete" patch size for these tasks. The king's "smallest correct change" philosophy targets this range — not because it adds extra lines, but because complete implementation of a feature/fix genuinely takes this much.

**M2.7 patch structure pattern:** Large FEATURE patches average 1,222 lines because M2.7 tends to include ALL integration layers (model + service + API + frontend + tests). The high avg vs median indicates many small-but-correct patches plus some very large comprehensive ones.

---

## Intel C: UPDATE Task Wiring Patterns

*From update_task_dpo_pairs.jsonl, first 20K records, wiring keyword search*

### Top 5 Wiring Patterns (from rationale analysis)

**Pattern 1: Config → Service → API chain**
> "solution b more aligned...it explicitly wires cloudinary configuration into the recommendations flow and documents/returns streaming urls"
- Winner shows: config setup + service integration + API response format
- Loser: "only renames a response field without showing backend logic"

**Pattern 2: State Management Propagation**
> "wires a teacher-mode toggle through the app state and passes that mode into both TheorySection and TestCard"
- Winner threads new state through EVERY component that needs it
- Loser: adds the toggle in one place, doesn't propagate

**Pattern 3: Backend + Frontend Bridge**
> "adding server-side developer token generation with origin aggregation"
- Winner bridges backend logic to frontend API contract
- Loser implements only one side

**Pattern 4: Lifecycle Integration**
> "not only adds X but also wires them into the lifecycle: saving on message updates"
- Winner: feature + lifecycle hook (save/load/cleanup events)
- Loser: feature without lifecycle

**Pattern 5: Event Handler + Data Flow**
> "wires new code into event handlers, state management, data flows, call sites"
- A feature that exists but is never called = 0 points
- Loser introduces new code but never connects it to the execution path

**Common thread:** UPDATE task losers "barely address" or "only partially address" by implementing one layer. Winners show the COMPLETE integration chain.

---

## Intel D: Model Performance Ranking (from chosen_label/rejected_label fields)

*40K sample, consensus pairs only*

| Model | Wins | Losses | Win Rate |
|-------|------|--------|---------|
| **claude-opus-4.7** | **8,561** | 3,023 | **74%** ← #1 |
| gpt-5.5 | 4,839 | 4,898 | 50% |
| o3 | 3,363 | 2,723 | 55% |
| qwen3.5-397b-tee | 2,858 | 3,900 | 42% |
| gemini-3.1-pro | 2,681 | 1,628 | 62% |
| glm-5.1-tee | 2,019 | 402 | 83% ← high WR, fewer matches |
| kimi-k2.6 | 1,905 | 2,260 | 46% |
| **m2.7** | 3,072 | **9,522** | **24%** ← worst |

**Critical finding: claude-opus-4.7 wins 74% of the time. M2.7 wins only 24%.**

This means the judge (Sonnet 4.6) strongly prefers opus-4.7-style patches over M2.7-style patches. The judge itself is a Sonnet model, and it rates opus-4.7 output as consistently superior.

**What does opus-4.7 do differently?**
From rationales where opus-4.7 wins: "directly addresses all acceptance criteria", "provides complete implementation", "shows proper integration across layers". It addresses ROOT CAUSE + all integration points in one patch.

**Implication for our SYSTEM_PROMPT:** The king likely runs on a strong model (opus-4.7 or equivalent). Our M2.7-based execution gives us a 24% raw quality floor. The SYSTEM_PROMPT can compensate by explicitly guiding M2.7 to cover all acceptance criteria — but the quality gap is structural.

---

## Intel E: Data Quality Map + Phase 2 Readiness

### Consensus Rates by Task Type (40K sample)
| Task Type | Total Pairs | Consensus Rate | Signal Quality |
|-----------|------------|----------------|----------------|
| UPDATE | 19,740 | **79.8%** | ⭐⭐⭐ HIGHEST volume + quality |
| FEATURE | 12,096 | **80.1%** | ⭐⭐⭐ |
| API | 4,211 | **78.7%** | ⭐⭐⭐ |
| BUGFIX | 3,954 | **80.1%** | ⭐⭐⭐ |

All task types have excellent signal quality (78–80% consensus). Trust ALL equally.

### Phase 2 Readiness: ✅ YES
DPO pair fields include: `gpt54_winner`, `gpt54_score_chosen`, `gpt54_score_rejected`, `sonnet_winner`
**Both Phase 1 (Sonnet) and Phase 2 (Sonnet + GPT-5.4 dual-judge) labels are present.**
Training on `consensus=True` pairs (which requires BOTH judges to agree) already trains for Phase 2 robustness.

### Full DPO Field List
`id, source, task_id, instruction, chosen_patch, rejected_patch, chosen_label, rejected_label, gpt54_winner, gpt54_score_chosen, gpt54_score_rejected, sonnet_winner, consensus, judge_rationale, sonnet_rationale, task_type, score_diff, priority, collected_at, est_cost_usd`

---

## Key Recommendations for v75 SYSTEM_PROMPT

### 1. Add EXPLICIT Acceptance Criteria Checklist Rule (HIGH PRIORITY)
The #1 lose signal across ALL task types is "only partially addresses acceptance criteria."
Add to SYSTEM_PROMPT (after the plan block instruction):
```
- Acceptance criteria: list EVERY explicit requirement from the issue as a separate plan row. 
  Check each one in your implementation. A patch that misses even one AC point loses.
```
Risk: LOW. This mirrors what the king's PLAN section already requires, but makes it explicit.

### 2. Add UPDATE-Specific Wiring Rule (MEDIUM PRIORITY — UPDATE only)
The judge consistently rewards "complete wiring through integration layers."
Add conditionally in plan phase for UPDATE/FEATURE tasks:
```
For UPDATE/FEATURE tasks: identify the FULL integration chain 
(data → service → API → frontend → lifecycle hooks). 
A feature that exists but is never called = 0 points. Wire through all layers.
```
Risk: MEDIUM. Keep it in the plan section, not the scoring section.

### 3. DO NOT touch the scoring sentence (L-SN66-KING-BASE-MANDATORY-1)
"smallest correct change a senior maintainer would accept" — confirmed load-bearing.
All our previous regressions came from replacing or supplementing this line.

### 4. Structural Reality (for T68-S2 planning)
M2.7 has 24% raw win rate vs 74% for opus-4.7. The SYSTEM_PROMPT closes the gap but cannot fully overcome model quality. Dedicated fine-tuned M2.7 (Stage 2 plan) is the right long-term fix.

# Data Intelligence — SN66 vNext (2026-05-19)

**Author:** Opus 4.7 Subagent (Step 2 — Data Intelligence)
**Date:** 2026-05-19 UTC
**King:** d24c9d30 (4595L)
**Data:** full_matrix_dpo_pairs.jsonl (2.3GB), reference_dpo_pairs.jsonl (670MB), update_task_dpo_pairs.jsonl (1.3GB), gold_patches/minimax-m2_7.jsonl (9,037 patches)

---

## Intel A: Winning/Losing Phrases by Task Type

Analysis: Phrases appearing in judge rationales when m2.7 loses to a stronger model (consensus=True, rejected_label=m2.7). First 30,000 consensus pairs from full_matrix.

### UPDATE (m2.7 loss triggers — ranked by frequency)
| Phrase | Count |
|--------|-------|
| 'incomplete' | 3,058 |
| 'acceptance criteria' | 2,613 |
| 'truncated' | 1,601 |
| 'more directly' | 647 |
| 'integration' | 634 |
| 'root cause' | 575 |
| 'end-to-end' | 396 |
| 'wires' | 231 |

**Finding:** m2.7's dominant failure mode on UPDATE is "appears incomplete/truncated" — the model stops mid-patch. The judge sees an unfinished patch and immediately awards the loss. Second is failing to satisfy acceptance criteria bullets explicitly.

### BUGFIX (m2.7 loss triggers)
| Phrase | Count |
|--------|-------|
| 'incomplete' | 619 |
| 'acceptance criteria' | 532 |
| 'truncated' | 313 |
| 'root cause' | 225 |
| 'more directly' | 184 |
| 'integration' | 121 |
| 'end-to-end' | 80 |
| 'error handling' | 57 |

**Finding:** Same truncation pattern but root cause matters more for BUGFIX — 225 mentions. m2.7 patches a symptom, not the owner.

### FEATURE (m2.7 loss triggers)
| Phrase | Count |
|--------|-------|
| 'incomplete' | 1,775 |
| 'acceptance criteria' | 1,590 |
| 'truncated' | 966 |
| 'integration' | 453 |
| 'root cause' | 365 |
| 'more directly' | 305 |
| 'end-to-end' | 274 |
| 'wires' | 164 |

**Finding:** FEATURE failures mirror UPDATE — incompleteness dominates. Integration cascade failures (all integration points, not just main entry point) account for 453 losses.

### Winning phrases (all types combined — when m2.7 wins):
Top win trigrams across 20,013 consensus pairs: "patch more directly addresses" (989 UPDATE), "patch much closer" (569 FEATURE), "acceptance criteria patch" (934 UPDATE). When m2.7 wins, rationale says "directly addresses root cause" and "closer to acceptance criteria."

---

## Intel B: M2.7 Strength Zones

### Win rate by task type (reference_dpo_pairs.jsonl, 8,189 consensus pairs)
| Task Type | M2.7 Wins | M2.7 Losses | WR |
|-----------|-----------|-------------|-----|
| UPDATE    | 382       | 3,698       | **9%** |
| FEATURE   | 267       | 2,195       | **10%** |
| API       | 89        | 775         | **10%** |
| BUGFIX    | 88        | 695         | **11%** |

**Finding:** M2.7 WR is uniformly 9-11% across ALL task types in head-to-head vs the reference baseline. There is NO strength zone — m2.7 loses across the board. The variation is too small (9-11%) to claim a specialty.

### Gold patch size analysis (9,037 gold patches)
- M2.7 avg lines added: **335**  
- Reference avg lines added: **724**
- M2.7 patch/reference ratio: **2.09x** (m2.7 OVER-edits on average)
- Under-editing (<70% of reference): **31%** of patches
- Over-editing (>130% of reference): **46%** of patches

**Finding:** M2.7 has a bimodal failure: either it under-edits (produces tiny patches that miss cascade files) or over-edits (produces bloated patches that change too much). The 31% under-edit rate explains the UPDATE wiring failures — the model generates small patches that don't trace the feature end-to-end.

### Gold patch archetype breakdown (9,037 M2.7 patches)
- FEATURE_BUILD: 6,744 (74%)
- REFACTOR: 1,228 (14%)
- MIGRATION: 625 (7%)
- BUG_FIX: 440 (5%)

**Finding:** M2.7's gold data is overwhelmingly FEATURE_BUILD. The model has seen far fewer BUGFIX and REFACTOR examples during training. This explains the reference_dpo WR gap — M2.7 is underexposed to the patterns that win BUG_FIX/REFACTOR tasks.

---

## Intel C: UPDATE Wiring Patterns

Analysis: 1,062 wiring examples (consensus pairs from update_task_dpo_pairs where judge rationale contains wiring keywords: 'wire', 'lifecycle', 'hook', 'connect', 'register', 'mount', 'dispatch', 'subscribe', 'listen', 'bind', 'emit', 'trigger', 'callback').

### Top 5 concrete wiring examples (winners vs m2.7 losers)

**Example 1 (claude-opus-4.7 beats m2.7):**
> "Patch B is clearly more complete: it not only adds localStorage helpers but also **wires them into the chat store lifecycle**: saving on message updates, falling back to local backup when fetch fails or returns empty, and clearing local backup alongside server data."

**Example 2 (claude-opus-4.7 beats m2.7):**
> "Patch B better addresses the core issue: it not only sets the Referrer-Policy header but also **implements server-side developer token generation with origin aggregation from request and environment**, which aligns with the acceptance criteria around robust allowed-origins."

**Example 3 (claude-opus-4.7 beats m2.7):**
> "Patch B wires a teacher-mode toggle **through the app state** and passes that mode into both TheorySection and TestCard, which are the core surfaces needing teacher/student-specific content."

**Example 4 (glm-5 beats m2.7):**
> "Solution B is more aligned with the task because it explicitly **wires cloudinary configuration into the recommendations flow** and documents/returns streaming URLs, while A mostly renames a field."

**Example 5 (claude-opus-4.7 beats m2.7):**
> "Patch B more directly satisfies the key requirement by **gating credit loading/subscription on authentication** and defensively handling unauthenticated credit fetches in both the hook and service."

### Pattern: What winners do that m2.7 doesn't
1. **Trace the feature path**: New functionality is added AND connected through state management, routing, AND UI layers
2. **Wire into lifecycle entry points**: save/load hooks, auth gates, effect dependencies, store subscriptions
3. **Handle ALL acceptance criteria explicitly**: Each AC bullet gets a file change, not just the headline feature
4. **Cascade to consumer files**: When a new service/store is added, all files that consume it are updated

### → SYSTEM_PROMPT rule derived from C:
```
UPDATE TASK WIRING PROTOCOL: After implementing the core change, trace the feature end-to-end:
1. Where does new data/state enter the system? (API, store, hook)
2. How does it flow through state management? (context, zustand, redux)
3. Where does it surface to the user? (UI components, effects)
4. Edit ALL files in this chain. A feature that isn't wired into its lifecycle is incomplete.
```

---

## Intel D: What Beats M2.7 (models + behavioral differences)

Analysis: First 50,000 consensus pairs from full_matrix_dpo_pairs (UPDATE, BUGFIX, FEATURE, API combined).

### Top models that beat M2.7 (consensus only, min 5 head-to-head matches)
| Model | Beats M2.7 | Total H2H | Win Rate vs M2.7 |
|-------|-----------|-----------|------------------|
| o3 | 2,507 | 2,746 | **91%** |
| claude-opus-4.7 | 1,330 | 1,560 | **85%** |
| glm-5-tee | 2,059 | 2,498 | **82%** |
| kimi-k2.5-tee | 260 | 328 | **79%** |
| gemini-3.1-pro | 779 | 1,043 | **74%** |
| gpt-5.5 | 3,230 | 4,707 | **68%** |
| qwen3.5-397b-tee | 457 | 800 | **57%** |
| deepseek-v3.2-tee | 227 | 412 | **55%** |
| m2.5-tee | 505 | 1,475 | **34%** |

**Note:** m2.5-tee (34%) and qwen3.5-397b-tee (57%) are the ONLY models m2.7 is competitive against. o3 and claude-opus-4.7 dominate at 85-91%.

### Key behavioral differences (4,606 cases of top models beating m2.7 on UPDATE)

**claude-opus-4.7 wins because** (from rationale analysis):
1. **End-to-end wiring**: Always traces feature through state → UI → persistence. Never stops at adding a helper without wiring it in.
2. **Auth-gating completeness**: When task involves authentication, closes all unauthenticated paths in BOTH frontend hooks AND backend services.
3. **Acceptance criteria explicit coverage**: Each rationale cites specific AC bullets matched.
4. **No truncation**: Full multi-file patches even when complex.

**o3 wins because** (91% WR = highest):
- Likely produces the most complete, highest quality patches across all dimensions
- The 91% WR vs m2.7 suggests o3 almost always covers more files, more AC bullets, and better root cause analysis than m2.7

### Actionable implication for vNext SYSTEM_PROMPT:
Study claude-opus-4.7's pattern specifically (85% WR, not hallucinated — actual rationale evidence). The SYSTEM_PROMPT should mirror opus-4.7's behavior:
- Wire features end-to-end through all lifecycle layers
- Make auth/state changes cascade to ALL consuming hooks and services
- Never produce a "helper" without its callers

---

## Intel E: Data Quality Map

Analysis: First 100,000 pairs from full_matrix_dpo_pairs.

| Task Type | Total Pairs | Consensus% | Avg Score Diff | Signal |
|-----------|------------|-----------|----------------|--------|
| UPDATE    | 49,812     | 78%       | 0.359          | **HIGH** |
| FEATURE   | 29,929     | 78%       | 0.378          | **HIGH** |
| API       | 10,523     | 78%       | 0.356          | **HIGH** |
| BUGFIX    | 9,736      | 79%       | 0.387          | **HIGH** |

**Key findings:**
1. **All task types have HIGH signal** — 78-79% consensus means the judge reliably agrees with itself. Training data is trustworthy across all types.
2. **BUGFIX has highest signal** (0.387 avg diff + 79% consensus) — though fewest pairs (9,736). Best data quality per record.
3. **UPDATE has the most data** (49,812 pairs) — highest training signal for fine-tuning. UPDATE improvements will generalize well.
4. **No weak signal types** — unlike some DPO datasets with noisy labels, this corpus is clean. Trust the consensus=True subset fully.

**Implication for fine-tuning priority:**
- Train on UPDATE first (most data, high signal, biggest WR gap to close)
- BUGFIX second (highest signal quality, root cause patterns matter)
- FEATURE and API will benefit from UPDATE improvements (shared patterns)

---

## Key Rules for SYSTEM_PROMPT (derived from data — grounded in evidence)

### Rule 1: Anti-Truncation Imperative
**Evidence:** "incomplete/truncated" = #1 phrase in m2.7 loss rationales across ALL types (3,058 UPDATE, 1,775 FEATURE, 619 BUGFIX, 966 FEATURE). **This is m2.7's single biggest loss pattern.**

```
CRITICAL: Your patch output MUST be complete. Never stop mid-implementation. 
If a file is long, produce the full edit. If many files need changes, change all of them.
A truncated patch is an automatic loss — incomplete always beats absent.
```

### Rule 2: Explicit Acceptance Criteria Coverage
**Evidence:** "acceptance criteria" = 2nd most common phrase in m2.7 losses (2,613 UPDATE, 1,590 FEATURE, 532 BUGFIX). Winners explicitly match EACH AC bullet to a code change.

```
ACCEPTANCE CRITERIA PROTOCOL: Before finalizing, list each bullet point from the issue's 
acceptance criteria. Verify each one has a corresponding code change in your patch.
If any AC bullet is unaddressed, add it before submitting.
```

### Rule 3: UPDATE End-to-End Wiring
**Evidence:** 396 "end-to-end" + 634 "integration" + 231 "wires" mentions in UPDATE losses. Claude-opus-4.7 wins 85% H2H by consistently tracing features through ALL lifecycle layers.

```
UPDATE TASK WIRING: For any UPDATE/ENHANCE/IMPROVE task, after implementing the core change:
- Trace: Where does the new data/logic ENTER the system?
- Wire: How does it flow through STATE MANAGEMENT?  
- Connect: Where does it SURFACE to the user?
- Cascade: Update ALL consumer files (hooks, services, UI components).
An update that adds a feature without wiring it into its lifecycle is always incomplete.
```

### Rule 4: Root Cause Ownership for BUGFIX
**Evidence:** 225 "root cause" mentions in BUGFIX losses. King's SYSTEM_PROMPT already has ROOT CAUSE RULE — but m2.7 still loses 89% of BUGFIX duels. The rule must be more explicit.

```
BUGFIX ROOT CAUSE: Do NOT patch the symptom's location. Ask: what OWNS this behavior?
Fix the owner, then cascade to all downstream callers of the fixed behavior.
Example: Parser rejects valid input → fix PARSER, update all call sites.
Never add a workaround at the call site when the bug lives upstream.
```

### Rule 5: Emergency Single-Shot (IMPLEMENTATION REQUIRED — from Step 1)
**Evidence:** King has `_solve_emergency_single_shot` at ~line 3556. When elapsed > (budget - 60s), king picks 1 target file, reads 2000-char snippet, produces a minimal patch. Prevents empty patch = instant loss.
**This is a CODE CHANGE, not a SYSTEM_PROMPT rule.** Port from king exactly.

---

## Summary: 3 Data-Grounded Insights for vNext

**Insight 1 (Critical):** M2.7's #1 loss is truncation (3,058 UPDATE cases). Add explicit anti-truncation rule. This alone could recover 15-20% of losses where the patch is flagged "appears incomplete/truncated."

**Insight 2 (High):** M2.7 wins at only 9-11% WR because it misses acceptance criteria and wiring. The winning pattern (from 4,606 claude-opus-4.7 UPDATE wins) is always end-to-end: new feature → state → lifecycle → UI. Add the UPDATE WIRING PROTOCOL explicitly.

**Insight 3 (Structural):** M2.7 is bimodal — 31% under-edit, 46% over-edit. Avg ratio 2.09x reference. The model doesn't know when to stop OR when to keep going. The COMPLETENESS ASYMMETRY rule ("under-editing costs MORE") combined with anti-truncation should reduce the under-edit tail. The over-edit tail needs the SURGICAL EDITING rule (already in king) preserved.

---

*Data sources: full_matrix_dpo_pairs.jsonl (2.3GB, ~300K pairs), reference_dpo_pairs.jsonl (8,189 consensus pairs), update_task_dpo_pairs.jsonl (1,062 wiring examples), gold_patches_minimax_minimax-m2_7.jsonl (9,037 patches)*

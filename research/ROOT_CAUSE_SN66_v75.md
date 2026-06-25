# ROOT CAUSE — SN66 v75 Pipeline
*Synthesis: 2026-05-20 UTC | Inputs: STEP1_SOURCE_INTEL_SN66_v75.md + DPO_INTEL_SN66_v75.md*
*Author: T68Bot Subagent (Step 3A Synthesis)*

---

## Executive Summary

- **Root cause:** Dual-layer failure — (1) M2.7 model quality gap vs opus-4.7 (24% vs 74% raw WR), partially overcome by SYSTEM_PROMPT, and (2) Acceptance Criteria (AC) coverage failure across all task types, especially UPDATE (38% WR) and API (30% WR).
- **Top 3 changes:** (1) Explicit AC checklist enforcement in plan block, (2) UPDATE/FEATURE wiring chain mandate, (3) Preserve scoring sentence exactly.
- **Confidence:** HIGH on diagnosis. MEDIUM on SYSTEM_PROMPT fix closing gap to ≥60%.

---

## 1. Why We're Losing (Root Cause)

### Layer 1: Model Quality Gap (Structural — 50 point ceiling problem)

The DPO data (40K pairs) is unambiguous:

| Model | Win Rate |
|-------|---------|
| claude-opus-4.7 | **74%** |
| gemini-3.1-pro | 62% |
| o3 | 55% |
| gpt-5.5 | 50% |
| qwen3.5-397b-tee | 42% |
| kimi-k2.6 | 46% |
| **M2.7 (our model)** | **24%** |

The judge (Sonnet 4.6) strongly prefers opus-4.7-style patches. The current king almost certainly runs on opus-4.7 or equivalent. Our M2.7 execution has a **50-point structural quality deficit** against the top model.

**What this means concretely:** Even with a perfect SYSTEM_PROMPT, M2.7 would need to punch 2× above its natural weight to reach 74%. The SYSTEM_PROMPT cannot fully overcome model quality. It can only guide M2.7 to hit the ceiling of what M2.7 is capable of producing.

**The 47.5% floor:** v74 (pure king clone, identical SYSTEM_PROMPT) achieved 47.5% WR. This is our current ceiling with M2.7 on the king's SYSTEM_PROMPT. The SYSTEM_PROMPT is worth ~23 percentage points above M2.7's raw 24% WR. Getting from 47.5% to 60%+ requires either model improvement OR finding specific SYSTEM_PROMPT changes that steer M2.7 to cover what it naturally misses.

**Task-type performance breakdown (v74 gate, 100 tasks, seed 42):**
- BUGFIX: ~50% — best task type for M2.7 (root cause focus aligns with M2.7 strengths)
- FEATURE: ~47% — close to BUGFIX, feature integration partially covered
- UPDATE: **38%** — significant weakness; UPDATE requires full integration chain coverage
- API/ROUTE: **30%** — worst; API requires "proper implementation" signaling that M2.7 struggles with

### Layer 2: Acceptance Criteria (AC) Coverage Failure

The DPO data identifies the #1 lose signal across ALL task types:

**"addresses acceptance criteria" / "better addresses acceptance criteria"**

From Intel A (40K DPO pairs, consensus):

| Task Type | AC Fail Signal | Frequency |
|-----------|---------------|-----------|
| UPDATE | "better addresses acceptance criteria" (LOSE-exclusive) | 1,094 |
| UPDATE | "addresses acceptance criteria" (WIN) | 624 vs LOSE 2,227 |
| API/ROUTE | "better addresses acceptance criteria" (LOSE-exclusive) | 218 |
| API/ROUTE | "addresses acceptance criteria" (WIN) | 116 vs LOSE 438 |
| FEATURE | "better addresses acceptance" (LOSE-exclusive) | 569 |

**The pattern is consistent:** When we lose, the judge says the king "better addresses acceptance criteria." When we win, the judge says our patch "directly addresses acceptance criteria." The word "better" in the LOSE rationale means: the king EXPLICITLY covered all AC points; we missed at least one.

**Why this affects M2.7 specifically:** M2.7's 24% raw WR suggests it does not naturally enumerate and check acceptance criteria exhaustively. The king's PLAN block format explicitly requires restating each requirement as its own row — this forces AC coverage. But M2.7 may not follow through from plan → implementation.

### Layer 3: UPDATE-Specific Wiring Failure (Compounding)

Intel C documents 5 UPDATE wiring patterns where winners show the COMPLETE integration chain:
1. Config → Service → API chain (winner wires cloudinary config through recommendations flow)
2. State Management Propagation (winner threads state through EVERY consuming component)
3. Backend + Frontend Bridge (winner bridges both sides; loser implements only one)
4. Lifecycle Integration (winner adds feature + lifecycle hooks: save/load/cleanup)
5. Event Handler + Data Flow (winner wires through event handlers AND call sites)

**Common failure mode:** UPDATE losers "barely address" or "only partially address" by implementing one layer. Our patches at 38% WR on UPDATE are hitting this exact failure — we implement the feature but don't wire it through all required layers.

**Interaction with model gap:** M2.7 at 24% raw WR is not naturally completing multi-layer integration. Even with the king's SYSTEM_PROMPT, UPDATE at 38% (below BUGFIX at 50%) shows that M2.7 still struggles with the wiring requirement.

---

## 2. King's Winning Formula

### 2.1 The Load-Bearing Scoring Sentence

```
Your patch is scored on (1) correctness/completeness vs the issue and hidden tests, and (2) 
similarity to a reference patch. Both reward the same thing: smallest correct change a senior 
maintainer would accept.
```

**Why this works:** It aligns the agent's optimization target directly with what the LLM judge evaluates. "Smallest correct change a senior maintainer would accept" primes the model to:
- Fix the root cause (not a symptom)
- Include all required integration layers (because a senior maintainer wouldn't ship incomplete wiring)
- Stay scoped (no hallucinated refactoring)

This sentence IS the task-type strategy. Every task type is implicitly covered by "what a senior maintainer would accept."

**Confirmed load-bearing:** v73 replaced this sentence with an explicit rubric (ROOT CAUSE RESOLUTION 40pts, SCOPE COMPLETENESS 30pts, etc.) and WR dropped from ~47-50% to 43-51%. The replacement created sub-objective gaming — M2.7 tried to optimize for the explicit rubric points instead of producing a complete correct patch.

### 2.2 The Plan Block Format

```
<plan>
- Requirement: restate every explicit issue requirement.
- Requirement: restate every secondary clause, edge case, "also"...
- Integration cascade: if the issue describes a feature spanning multiple concerns... 
  enumerate EVERY required integration point as its own plan row
- Likely target: name likely files/functions/classes/modules
- Strategy: smallest root-cause fix likely to satisfy the issue.
- Verification: targeted test command expected after patching.
</plan>
```

**Why this works:** Forces the model to explicitly enumerate requirements and integration cascades BEFORE writing code. This is the AC coverage mechanism — restate every requirement = never miss an AC point. "Integration cascade" is the UPDATE wiring mechanism — enumerate every integration point = never miss a layer.

**The gap:** The king's PLAN block is well-structured but does not explicitly say "check each AC point in your implementation." M2.7 may plan correctly but not execute fully through all plan rows.

### 2.3 The Completeness Asymmetry Sentence

```
Under-editing (missing a cascade file) is penalized MORE than slight over-editing.
```

**Why this works:** Counteracts M2.7's natural tendency toward minimal patches. Without this, M2.7 stops at "smallest" and misses integration files. With this, M2.7 includes borderline cascade files.

### 2.4 The INSPECTION STRATEGY

```
"Preloaded snippets first, then ONE or TWO focused searches."
```

**Why this works:** Forces fast first-edit behavior. King wins on quick targeted edits; our agents lose turns on over-inspection. The king's budget pressure prompts (step 4+) reinforce this.

### 2.5 The Multishot Wrapper (v28)

- Runs inner solve twice if first attempt is low-signal (< 5 substantive hunks)
- Bootstrap second attempt from first attempt failures
- Emergency single-shot fallback if both empty
- `_patch_duel_score()` picks winner between two attempts

**Why this matters:** Even with M2.7's quality gap, two attempts + cherry-pick gives a better expected outcome. This is already in our v75 base (copied from king).

### 2.6 What King Does NOT Have

- No TASK-TYPE STRATEGY section (added to v73, hurt WR)
- No explicit rubric with point weights (added to v73, hurt WR)
- No ANTI-TRUNCATION IMPERATIVE section
- No ACCEPTANCE CRITERIA PROTOCOL section beyond the plan block

**The king's approach:** Trust the agent to follow the plan block format. Do not add compensating rules. The plan block + scoring sentence + completeness asymmetry is the complete strategy.

---

## 3. Our Change History Analysis (v71–v74)

### v73 — Primary Regression Source

**What changed:**
1. Replaced scoring sentence with 9-line explicit rubric ("ROOT CAUSE RESOLUTION 40pts, SCOPE COMPLETENESS 30pts...")
2. Added 4 rule blocks (~56 lines): ANTI-TRUNCATION IMPERATIVE, ACCEPTANCE CRITERIA PROTOCOL, UPDATE/ENHANCE TASK WIRING RULE, TASK-TYPE STRATEGY

**Why it failed:**
- Scoring sentence replacement: M2.7 started gaming the explicit rubric instead of producing complete patches
- Rule blocks: 56 extra lines dilute attention; M2.7 has limited context following reliability at this depth
- TASK-TYPE STRATEGY with file count targets: artificial constraints that hurt non-UPDATE tasks
- ACCEPTANCE CRITERIA PROTOCOL: redundant with plan block format, created confusion

**WR result:** ~43-51% (below v74 king clone at 47.5%)

### v71–v72 — Setup for v73 Failure

Based on the pattern (v73 doc says v71-v73 all showed 43-51% WR), these versions likely made similar "add more rules" mistakes:
- Adding explicit sections that conflicted with "smallest correct change" philosophy
- Rule bloat diluting the core scoring alignment
- Possible: added "never delete" pattern (confirmed catastrophic in v59: REFACTOR collapsed to 0%)

### v74 — Correct Diagnosis, Incomplete Solution

**What changed:** Pure king clone — removed ALL v71-v73 additions, restored king's SYSTEM_PROMPT exactly.

**Expected:** ~90% WR (based on challenger bias hypothesis from small sample)
**Actual:** 47.5% WR

**Why the 90% prediction failed:** The 10-task king-vs-king test showing 90% WR was a sampling artifact. The challenger bias (position effect) is NOT reliably ~90% — it's more like ~2-3% or not statistically significant at scale. The 47.5% result is real performance.

**What this means for v75:** v74 already stripped bad additions. v75 starts from a clean king clone base. The remaining 47.5% → 60%+ gap must come from targeted improvements, not just removal of bad content.

### Common Failure Mode Across v71–v74

**Pattern:** Add explicit rules trying to address observed weaknesses → dilute core alignment → net negative or neutral WR.

**Root cause of this pattern:** We were solving a SYSTEM_PROMPT problem when the real problem is model quality (M2.7 24% raw WR). SYSTEM_PROMPT changes have diminishing returns once you've hit the king's baseline. The remaining gap is model-level, not instruction-level.

---

## 4. Top 3 Changes for v75 (SPECIFIC)

### Change 1: Explicit AC Coverage Verification in Plan Block

**Target problem:** UPDATE (38% WR) and API (30% WR) failures — "only partially addresses acceptance criteria" is the #1 lose signal in DPO data.

**Exact text to add:** Insert immediately after the current plan block instruction ends (after the `Verification:` line), before the `</plan>` format example:

```
- AC checklist: after listing all requirements above, explicitly state: "All AC points covered: [yes/no for each]". If any AC point is not yet covered, add a specific step to address it before finishing.
```

**Where to add it:** In the SYSTEM_PROMPT plan block format description, as the final bullet in the plan format list.

**Expected WR impact:**
- UPDATE: +5-10% (directly targets "only partially addresses acceptance criteria" failure)
- API/ROUTE: +5-8% (same AC coverage failure pattern)
- FEATURE: +3-5% (moderate AC coverage issue)
- BUGFIX: 0-2% (BUGFIX already scores ~50%; root cause rule covers AC implicitly)

**Risk of regression:** LOW. The king already requires requirement enumeration in the plan block. This adds a verification step that forces M2.7 to self-check coverage. It does NOT replace the scoring sentence or add conflicting philosophy.

**Constraint check:**
- ≤10 lines: ✅ (1 bullet point, ~30 words)
- Does not touch scoring sentence: ✅
- Targets specific DPO failure: ✅ (Intel A, "addresses acceptance criteria" signal)

---

### Change 2: UPDATE/FEATURE Integration Chain Wiring (Conditional)

**Target problem:** UPDATE 38% WR specifically — DPO Intel C shows 5 wiring patterns that judges reward. M2.7 implements features but fails to wire through all integration layers.

**Exact text to add:** Insert in LANGUAGE-SPECIFIC COMPLETENESS RULES section (or after SURGICAL EDITING section if cleaner), as a conditional rule:

```
UPDATE AND FEATURE TASKS — WIRING COMPLETENESS:
A feature that exists but is never called scores zero. Trace the FULL execution chain: 
data model → service layer → API endpoint → frontend/consumer → lifecycle hooks → call sites. 
Every layer mentioned in the issue must be wired through. Check call sites last.
```

**Where to add it:** After the LANGUAGE-SPECIFIC COMPLETENESS RULES header but before the per-language breakdown. This position is read AFTER the scoring sentence, so it supplements rather than contradicts.

**Expected WR impact:**
- UPDATE: +8-12% (directly targets Intel C patterns)
- FEATURE: +3-5% (partial wiring failure in FEATURE too)
- BUGFIX: 0% (BUGFIX rarely involves multi-layer wiring)
- API/ROUTE: +2-4% (partial: API tasks need "proper implementation" but wiring already partially covered)
- REFACTOR: 0% (wiring is not the issue; scope discipline covers REFACTOR)

**Risk of regression:** MEDIUM. Adding any block has cognitive cost. However:
- This targets the SPECIFIC documented failure mode (Intel C wiring patterns)
- It is placed AFTER the scoring sentence (not conflicting with it)
- It supplements the integration cascade in the plan block rather than contradicting it
- ~50 words total — within the ≤10 lines constraint

**Constraint check:**
- ≤10 lines: ✅ (5 lines)
- Does not touch scoring sentence: ✅
- Targets specific DPO failure: ✅ (Intel C, UPDATE wiring patterns)

---

### Change 3: Preserve Scoring Sentence EXACTLY (Non-Change)

**Exact text that must remain unchanged:**
```
Your patch is scored on (1) correctness/completeness vs the issue and hidden tests, and (2) 
similarity to a reference patch. Both reward the same thing: smallest correct change a senior 
maintainer would accept.
```

**This is the most important "change" for v75:** Do not touch it. Do not add to it. Do not rephrase it. Do not add a parenthetical.

**Why stated explicitly:** v73 replaced it, causing confirmed regression. v72/v71 likely modified it. The STEP1 intel explicitly flags this as "LOAD-BEARING." Every pipeline run must re-confirm this sentence is byte-identical to the king's.

**Verification command:**
```bash
grep -n "smallest correct change" /root/sn66-ninja/agent_cl_gpt_v75.py
# Must match: line ~2831, exact text above
```

**Expected WR impact:** Preserving this = preserving 47.5% baseline. Modifying it = confirmed regression to ~43%.

---

### Combined Expected WR With All 3 Changes

| Task Type | Baseline (v74) | Change 1 (AC) | Change 2 (Wiring) | Combined |
|-----------|---------------|--------------|------------------|---------|
| BUGFIX (50 tasks) | 50% | +1% | 0% | **51%** |
| FEATURE (19 tasks) | 47% | +4% | +4% | **55%** |
| UPDATE (13 tasks) | 38% | +8% | +10% | **56%** |
| API/ROUTE (10 tasks) | 30% | +6% | +3% | **39%** |
| REFACTOR (5 tasks) | ~47% | +1% | 0% | **48%** |
| OTHER (3 tasks) | ~47% | +1% | 0% | **48%** |
| **Overall (100 tasks)** | **47.5%** | **+3.5%** | **+4.5%** | **~55.5%** |

**Honest assessment:** ~55% estimated WR with both changes. This is above the 47.5% baseline but likely below the ≥60% gate threshold. The model quality gap (M2.7 24% vs opus-4.7 74%) is the binding constraint — SYSTEM_PROMPT changes can steer M2.7 to cover its natural gaps but cannot make M2.7 produce opus-4.7-quality patches.

---

## 5. What NOT to Do (Confirmed Bad)

### ❌ FORBIDDEN: Replace or modify the scoring sentence

```
# NEVER replace this line:
"Both reward the same thing: smallest correct change a senior maintainer would accept."
```

**Evidence:** v73 replaced it → WR dropped from 47.5% to ~43-51%. STEP1 Finding 3: "v73's biggest sin."
**Lesson ID:** L-SN66-SCORING-SENTENCE-LOAD-BEARING-1

---

### ❌ FORBIDDEN: Add explicit rubric with point weights

```
# NEVER add anything like:
ROOT CAUSE RESOLUTION: 40 points
SCOPE COMPLETENESS: 30 points
PATCH SIMILARITY: 30 points
```

**Evidence:** v73 added this format → M2.7 games the rubric instead of producing complete patches.
**Why it fails:** Explicit rubrics create optimization targets that diverge from "smallest correct change" philosophy.

---

### ❌ FORBIDDEN: Add TASK-TYPE STRATEGY section with file count targets

```
# NEVER add anything like:
BUGFIX tasks: target 1-3 files
FEATURE tasks: target 3-7 files
UPDATE tasks: target 2-5 files
```

**Evidence:** v73 added this → artificially constrained patch scope; contradicts "let integration cascade drive file count."
**Alternative:** The plan block's integration cascade already handles this dynamically.

---

### ❌ FORBIDDEN: Add "never delete" or "preserve existing code" rules

```
# NEVER add anything like:
"Never delete or remove existing functions/components unless explicitly requested"
"Preserve existing code structure"
```

**Evidence:** v59 added this → REFACTOR WR collapsed from 60% → 0%. UPDATE WR dropped from ~40% → 27%.
**Lesson ID:** L-SN66-NEVER-DELETE-RULE-1

---

### ❌ FORBIDDEN: Add ANTI-TRUNCATION IMPERATIVE section

**Evidence:** v73 added this as 14-line block → conflicted with "smallest correct change" → net negative.
**Root cause:** M2.7 interpreted anti-truncation as "always add more lines" → violated completeness vs minimalism balance.

---

### ❌ FORBIDDEN: Multiple large rule blocks stacked together

**Pattern:** v73 added 4 sections (56 lines total) → cognitive overload → M2.7 attention dilution → WR drops.
**Rule:** Any single addition to king base must be ≤10 lines. If you need more than 10 lines to express a rule, it's probably two rules that need individual testing.

---

## 6. Decision: Is a SYSTEM_PROMPT Change the Right Move?

### The Honest Assessment

**Model quality gap is the binding constraint:**
- M2.7 raw WR: 24% (DPO Intel D)
- opus-4.7 raw WR: 74%
- Gap: 50 percentage points

**What SYSTEM_PROMPT can do:**
- SYSTEM_PROMPT (king's) + M2.7 = 47.5% WR → worth +23.5 points above M2.7 raw
- Optimized SYSTEM_PROMPT + M2.7 = estimated 55-58% WR → maybe +8-10 more points
- Best realistic ceiling for M2.7 with SYSTEM_PROMPT: ~58-62%

**Whether ≥60% is achievable with SYSTEM_PROMPT alone:** UNCERTAIN. The estimated combined WR is ~55.5% from changes 1+2. Reaching 60% may require either:
- (a) Additional SYSTEM_PROMPT improvements beyond what DPO data directly supports, OR
- (b) Model upgrade to opus-4.7 or fine-tuned M2.7

### What SYSTEM_PROMPT Cannot Fix

The DPO data shows opus-4.7 wins because it "directly addresses all acceptance criteria" and "provides complete implementation across layers." This is output quality, not instruction following. When M2.7 loses on UPDATE at 38%, it's not because M2.7 didn't read the wiring rule — it's because M2.7 at 24% raw WR simply doesn't produce the same depth of multi-layer integration that opus-4.7 does natively.

### Recommended Path for v75

**YES, attempt SYSTEM_PROMPT changes** (Changes 1+2 above) with the following expectations:
- Expected WR: 53-58% (above 47.5% baseline, likely below 60% gate)
- If gate result is 55-59%: declare partial success, prioritize model upgrade (fine-tuned M2.7 on gold data)
- If gate result is ≥60%: submit immediately, capture lessons on what worked
- If gate result is ≤50%: revert to pure king clone (v74 base), escalate to model upgrade

**The long-term fix (Task 4 in TOOLS.md):**
Dedicated fine-tuned M2.7 on 200K+ SN66 gold patches + 30K DPO pairs = custom model that closes the quality gap from the training data side. The SYSTEM_PROMPT changes buy time while the fine-tune is prepared.

### Confidence Level by Section

| Claim | Confidence |
|-------|-----------|
| M2.7 raw WR is 24% | HIGH (DPO Intel D, 40K pairs) |
| AC coverage is #1 lose signal | HIGH (Intel A, consistent across all task types) |
| UPDATE wiring failure is secondary cause | HIGH (Intel C, 5 clear patterns) |
| Change 1 (AC checklist) will help | MEDIUM (mechanism is right; M2.7 may not follow through) |
| Change 2 (Wiring rule) will help UPDATE | MEDIUM (same caveat) |
| Combined WR will reach ≥60% | LOW-MEDIUM (structural model gap may prevent this) |
| Fine-tuned M2.7 is the real solution | HIGH (model quality is the binding constraint) |

---

## 7. v75 Build Specification (For Step 4 — Build)

### Base
`/root/sn66-ninja/agent_cl_gpt_v75.py` (4595L, pure king copy, commit d24c9d30)

### Verified Prerequisites (from Step 1 intel)
- [x] Scoring sentence at line ~2831 — preserved
- [x] Completeness asymmetry — preserved
- [x] Multishot wrapper (v28) — preserved
- [x] Blind A/B judge (PR #40) — harness v6 current
- [x] Kimi fallback (PR #37) — harness v6 current

### Changes to Apply

**Change 1 — AC Coverage Verification**
Location: SYSTEM_PROMPT, plan block format section, after `Verification:` bullet, before closing format description
Text:
```
- AC checklist: after listing all requirements above, explicitly state: "All AC points covered: [yes/no for each]". If any AC point is not yet covered, add a specific step to address it before finishing.
```

**Change 2 — UPDATE/FEATURE Wiring Completeness**
Location: After LANGUAGE-SPECIFIC COMPLETENESS RULES header, before per-language breakdown
Text:
```
UPDATE AND FEATURE TASKS — WIRING COMPLETENESS:
A feature that exists but is never called scores zero. Trace the FULL execution chain: 
data model → service layer → API endpoint → frontend/consumer → lifecycle hooks → call sites. 
Every layer mentioned in the issue must be wired through. Check call sites last.
```

**Change 3 — Verification command (builder must run before gate)**
```bash
grep -n "smallest correct change" /root/sn66-ninja/agent_cl_gpt_v75.py
# Expected: exactly 1 match at ~line 2831
```

### Gate Test
```bash
tmux new-session -d -s sn66_v75_gate100
tmux send-keys -t sn66_v75_gate100 \
  "cd /root/sn66-ninja && python3 -u validator_harness_v6.py \
   --challenger agent_cl_gpt_v75.py \
   --king king_agent.py \
   --tasks 100 --seed 42 --parallel 3 --timeout 600 2>&1 | tee /tmp/v75_gate100.log" Enter
```

**Threshold:** ≥60% decisive WR (gate policy per AGENTS.md directive 2026-05-17)
**Fallback:** If <55%, revert to pure v74 king clone and escalate to model upgrade decision

---

## References

- STEP1_SOURCE_INTEL_SN66_v75.md — King analysis, duel data, harness config
- DPO_INTEL_SN66_v75.md — DPO Intel A-E (40K pairs)
- AGENTS.md — L-SN66-NEVER-DELETE-RULE-1, L-SN66-BLIND-JUDGE-1, L-SN66-GATE-CLEANUP-1
- DPO dataset: /root/sn66-ninja/training_data/dpo/ (30K+ pairs)
- Gold data: /root/sn66-ninja/training_data/training_unified_gold.jsonl (200K+ records)

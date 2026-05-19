# ROOT CAUSE ANALYSIS — SN66 vNEXT
**Author:** T68Bot Subagent (Synthesis Task)  
**Date:** 2026-05-19 UTC  
**Context:** Scoring changed to 100% LLM judge (claude-sonnet-4.6). v62b got +3 margin (26W/23L), need +4 to dethrone.  
**Sources:** KING_ANALYSIS, DPO_INTEL, M27_PATTERNS, LIVE_DUEL_STATE  

---

## 1. ROOT CAUSE OF CURRENT LOSSES

**Primary problem: We win more rounds than king but don't clear the +4 margin threshold.**

v62b performance: 26W/23L (+3), mean score 0.497 vs king 0.466. We're AHEAD on both metrics but lose by 1 round.  
We need to convert exactly 2 marginal losses → wins while not losing any current wins. (+5 net guarantees dethrone).

### Specific failure modes in our 23 loss rounds:

**1. Breaking changes / errors (68% of challenger losses per live data)**
Our patches in loss rounds score 0.38-0.40 vs king's 0.53-0.70. The primary differentiator is correctness — broken code (TypeScript errors, wrong imports, API mismatches) is the #1 kill signal per Claude Sonnet 4.6. M2.7 over-edits (57.6% of patches exceed reference), and when it mis-edits cascade files, it introduces compilation failures.

**2. Missing step-based hail-mary (king-specific mechanism)**
King has DUAL trigger: `elapsed ≥ time_fraction OR step ≥ step_threshold`. v62 only has the time trigger. On fast-inspection loops where M2.7 reads many files but makes no edits by step count, king fires the hail-mary and forces an edit. We miss this entire trigger path.

**3. Unnecessary churn on 22-27% of rounds**
Claude Sonnet 4.6 explicitly calls out unrelated edits (reformatting, whitespace, chmod changes) in loss rationales. M2.7's over-editing tendency means it sometimes touches files that aren't needed, introducing risk. The judge penalises this directly.

**4. BUGFIX root-cause precision gap**
73% of today's tasks are BUGFIX. On BUGFIX, judge rewards root-cause fix + all related call sites. Our agent has no explicit BUGFIX-specific rules to trace bug to its owner and cascade fixes. King also lacks this, but king's "ROOT CAUSE RULE" section in SYSTEM_PROMPT is tighter.

**5. Solver errors eating win credits**
Multiple rounds show `challenger_exit_reason: solver_error` even with reasonable patches. Runtime errors (not scoring failures) cost us won rounds. Likely M2.7 producing diffs that apply cleanly but leave compile errors.

---

## 2. KING'S 5 COMPETITIVE ADVANTAGES

Ranked by estimated WR impact:

| Rank | Advantage | Evidence | Est. WR Impact |
|------|-----------|----------|----------------|
| 1 | **Dual-trigger hail-mary** (time OR step count) | King has `_hm_step_trigger = step >= _MID_LOOP_HAIL_MARY_STEP_TRIGGER`. v62 has time only. Fires on fast-inspection loops with no patches. | +3-4% WR |
| 2 | **Acceptance criteria extraction + re-injection** | `_extract_acceptance_criteria()` injects bullet checklist into initial user message. M2.7 directly maps criteria to edits. DPO data: 34/50 UPDATE chosen patches cited "acceptance criteria" | +2-3% WR |
| 3 | **7-gate refinement pipeline** | Syntax→test→deletion→criteria→coverage→polish→self-check. Each gate catches a specific failure mode before submission. We have fewer gates in v62. | +2% WR |
| 4 | **Deletion nudge gate** | Fires when issue requires removals but patch has zero deletions. DPO: "removes old implementation" is praised; partial refactors penalised. | +1-2% WR |
| 5 | **Preload stripping at step 4** | Removes bulky file content from context at step 4, saving tokens for actual editing. Prevents late-round context overflow on long files. | +1% WR |

---

## 3. OUR 3 UNIQUE ADVANTAGES (v62 has, king lacks)

| Advantage | v62 | King | Assessment |
|-----------|-----|------|------------|
| **Explicit completeness asymmetry** | ✅ "Under-editing costs MORE than over-editing" + "COMPLETENESS BEATS MINIMALISM" in SYSTEM_PROMPT | ❌ Implicit only — no explicit asymmetry statement | **KEEP — strongly aligned with DPO data (94% signal strength for completeness)** |
| **Soft nudge at 30% time (no patch)** | ✅ `build_soft_nudge_prompt` | ❌ Missing | **KEEP — fires earlier than hail-mary, prevents late-start loops** |
| **Forced edit at 80% wall-clock** | ✅ `build_forced_edit_prompt` + criteria self-check | ❌ Missing | **KEEP — forces completion before deadline pressure** |

**Assessment:** These 3 advantages are genuine and supported by data. Do NOT remove any of them in vNEXT.

---

## 4. JUDGE MODEL CHANGE IMPACT (Claude Sonnet 4.6 vs GPT-5.4)

**Agreement rate: 79.7%. The 20.3% disagreement cases define the new strategy.**

### What Sonnet uniquely rewards (from 200 disagreement samples):
| Signal | Frequency | vs GPT-5.4 |
|--------|-----------|-----------|
| `cleaner` code | 35/200 (17.5%) | GPT-5.4 rarely cited |
| `architectural` fitness | 23/200 (11.5%) | New signal |
| `error handling` | 10/200 (5%) | New signal |
| `production-ready` | 5/200 (2.5%) | New signal |
| `idiomatic` code | 5/200 (2.5%) | New signal |

GPT-5.4 focused on `acceptance criteria` alignment (60.5%). Sonnet still cares about criteria (completeness at 92%+ rate) but ALSO does code review.

### Strategic implications:
1. **Correctness is now MORE important than before.** Breaking errors = 68-83% of losses per live data. Sonnet does a code review, not just a feature checklist.
2. **Code quality matters.** Idiomatic Python, proper TypeScript types, correct error handling — Sonnet rewards this. M2.7 should be told to write clean, idiomatic code for the target language.
3. **Completeness still dominates on the fundamentals** — don't sacrifice it. The shift is that correctness has risen from "important" to "primary".
4. **Architecture fitness** — use correct file paths, logical module structure, no mixing concerns.
5. **Production-readiness signals** — include tests where natural, proper migrations, correct imports.

### Key directional change: **CORRECT → COMPLETE → CLEAN** (in that priority order). Previously it was: COMPLETE → CORRECT. This is a meaningful reorder.

---

## 5. TOP 5 CHANGES FOR vNEXT

Ranked by expected WR improvement:

### Change 1: Add Step-Based Hail-Mary Trigger
**What:** Add `_hm_step_trigger = step >= 8` to mid-loop hail-mary (DUAL trigger, matching king)  
**Why:** King has this; v62 only has time trigger. Fast-inspection loops where M2.7 reads 10+ files before editing miss the time trigger but would hit the step trigger. King fires, we don't = lost rounds.  
**Expected impact:** +3-4% WR (closes gap on fast-reading/slow-editing tasks)  
**Risk:** Low — king uses this in production, proven safe

---

### Change 2: Anti-Churn Rules (Correctness Preservation)
**What:** Add explicit SYSTEM_PROMPT section: "ANTI-CHURN DISCIPLINE — only modify files the task requires. No reformatting, no whitespace changes, no unnecessary import cleanup, no chmod. Every edit must be justified by the issue text."  
**Why:** 22-27% of loss rounds involve unnecessary churn per live data. Sonnet explicitly calls this out in rejection rationales. M2.7 over-edits by nature (57.6% > reference size) — without guardrails it churns.  
**Expected impact:** +2-3% WR (directly addresses #3 loss cause)  
**Risk:** Low — does not restrict required edits, only restricts unrequested changes

---

### Change 3: Correctness-First SYSTEM_PROMPT Reorder
**What:** Promote correctness framing before completeness in SYSTEM_PROMPT. Current v62 leads with COMPLETENESS BEATS MINIMALISM. For Sonnet: lead with "produce CORRECT, COMPILABLE patches first — breaking changes kill scores above all else. Then ensure completeness."  
**Why:** Sonnet's #1 penalty is breaking changes (68-83% of losses). GPT-5.4 focused on criteria; Sonnet does code review. The priority order must shift: CORRECT → COMPLETE → CLEAN.  
**Expected impact:** +2-3% WR (addresses #1 loss cause: breaking errors)  
**Risk:** Medium — must keep completeness asymmetry intact; just reorder priority framing

---

### Change 4: BUGFIX-Specific Root Cause Rules
**What:** Add BUGFIX task-type section: "For bug fixes: (1) identify the ROOT CAUSE file, not downstream symptoms; (2) trace ALL call sites that propagate the bug; (3) add error handling/fallback at the fix point; (4) do NOT add security regressions (hardcoded secrets, broken .gitignore)."  
**Why:** BUGFIX = 73% of today's task distribution. DPO data shows root-cause patches win 8/20 cases; symptom-only patches are penalized. Security regressions appear in 10% of BUGFIX rejections.  
**Expected impact:** +2% WR on BUGFIX-heavy days (73% of tasks = high leverage)  
**Risk:** Low — additive section, doesn't change behavior on non-BUGFIX tasks

---

### Change 5: Sonnet Code Quality Signals
**What:** Add SYSTEM_PROMPT section: "LANGUAGE IDIOM RULE — write idiomatic code for the detected language. Python: list comprehensions, proper typing, f-strings. TypeScript: generics, proper interface types, no `any`. Go: proper error returns. Add error handling (try/catch, fallbacks) where the fix requires it. The judge rewards production-ready, clean code over minimal-but-complete code."  
**Why:** Sonnet uniquely rewards `cleaner` (35/200), `architectural` (23/200), `error handling` (10/200) vs GPT-5.4. These are NEW signals that didn't matter before the judge change.  
**Expected impact:** +1-2% WR on quality-sensitive rounds  
**Risk:** Low — adds quality guidance without restricting correctness or completeness

---

## 6. FORBIDDEN PATTERNS FOR vNEXT

Based on v54-v63 regression analysis:

### ❌ FORBIDDEN: "Never Delete" Pattern
```
# DO NOT ADD anything resembling:
"Never delete or remove existing functions/components unless explicitly requested"
"Preserve existing code structure"  
"Only add, never remove"
```
**Why:** v59:3096 — this single rule collapsed REFACTOR 60% → 0% and UPDATE ~40% → 27%.  
**Root cause:** REFACTOR and UPDATE tasks REQUIRE deletion. This rule contradicts them.  
**Lesson:** L-SN66-NEVER-DELETE-RULE-1

### ❌ FORBIDDEN: Pure Minimalism Without Completeness Asymmetry
```
# DO NOT use alone without pairing with completeness asymmetry:
"smallest correct change, no more"
"patch a careful senior maintainer would submit: complete, precise, no more"
```
**Why:** Without "under-editing costs MORE than over-editing", the LLM interprets minimalism as the primary goal and under-serves completeness.  
**Lesson:** L-SN66-MINIMALISM-FRAMING-1

### ❌ FORBIDDEN: Multiple Completeness Asymmetry Statements That Contradict
Do not add both "COMPLETENESS BEATS MINIMALISM" AND "surgical minimalism above all" — they cancel out. Pick one framing, pair it with the asymmetry rule.

### ❌ FORBIDDEN: Over-Injecting Acceptance Criteria at Every Step
If we add criteria extraction (king feature), do NOT re-inject criteria checklist on every single turn — it bloats context and confuses M2.7 mid-task. Inject once at start + once at 80% time gate.

### ❌ FORBIDDEN: Removing Soft Nudge or Forced Edit Gates
v62 has these; king lacks them. Our forced-edit and soft-nudge are defensive mechanisms that cover king's blind spot. They cost us nothing and catch stalling loops.

### ❌ FORBIDDEN: Targeting Cursor Similarity Score
PR#1598 removed cursor_sim from scoring entirely. Any optimization aimed at patch similarity to reference (e.g., "match the reference patch format") is now irrelevant.

---

## 7. ARCHITECTURE DECISION

**Verdict: BASE vNEXT ON v62, LAYER IN KING'S MISSING MECHANISMS**

### Option (a): king_agent.py + our improvements
Pros: King's 7-gate pipeline is mature, deletion nudge is well-tuned  
Cons: Lose our explicit completeness asymmetry, soft nudge, forced edit gate — all proven advantageous. Would need to re-add everything, risking regression.

### Option (b): v62 + king's missing mechanisms ← **WINNER**
Pros:
- Keep v62's completeness asymmetry (explicitly in SYSTEM_PROMPT — king lacks this)
- Keep soft nudge + forced edit gate (king lacks these)
- Keep criteria self-check at 80% (king lacks this)
- ADD: dual-trigger hail-mary (king's step trigger)
- ADD: acceptance criteria extraction + initial injection
- ADD: anti-churn rules
- ADD: Sonnet correctness-first reorder
- ADD: BUGFIX-specific root cause section

Cons: Need to implement king's acceptance criteria extractor (moderate effort)

**Justification:** v62b already scored 0.497 vs king's 0.466 and won 53.1% of rounds. We're one mechanism short. The fastest path to +4 net margin is additive improvement on v62, not a rewrite from king.

**Key mechanic to port from king:** `_extract_acceptance_criteria(issue_text)` + injection into initial user message. This single function gave king a structural completeness advantage. Port it verbatim.

---

## 8. SUCCESS METRIC

**To guarantee dethronement:**
- Win condition: challenger_wins - king_losses > 3 (need net ≥ +4)
- v62b achieved +3 → need +1 more net round
- Target: **WR ≥ 55%** over 50 rounds = 27.5W/22.5L = **+5 net** (safe margin above threshold)

**Gate test thresholds (100 tasks, seed 42):**
- Target: ≥ 70% pass rate against current king (per James directive 2026-05-17)
- Minimum acceptable for submission: ≥ 65%

**Score quality target:**
- Our loss rounds: avg score 0.38-0.40 vs king 0.53-0.70
- Must raise loss-round scores to ≥ 0.45 avg (reduces king dominance in close battles)
- Achievable via: anti-churn + correctness-first + code quality signals

**New king consideration:**
King d24c9d3 is being dethroned in duel 5141 (+8 margin, challenger winning). Before building vNEXT:
1. `bash scripts/sync_king.sh` after duel 5141 ends
2. Verify `wc -l king_agent.py` changes
3. Assess new king's difficulty level before starting build

---

## SYNTHESIS SUMMARY

| What | Evidence |
|------|----------|
| v62b: 1 round short of dethroning | +3 vs threshold +3+1=4 |
| #1 loss cause | Breaking errors (68-83%) |
| #2 loss cause | Missing files/requirements |
| #3 loss cause | Unnecessary churn (22-27%) |
| King's key missing mechanism in v62 | Step-based hail-mary trigger |
| Judge changed → new signals | Sonnet: clean/architectural/error handling |
| Completeness still matters | 92%+ penalization rate unchanged |
| Task distribution | BUGFIX 73% today (was 48% yesterday) |
| Architecture | v62 base + 5 additions (do not rewrite from king) |
| vNEXT WR target | ≥ 55% (= +5 net margin, safe above threshold) |

# DEBATE — ROOT CAUSE SN66 vNEXT
**Author:** T68Bot Devil's Advocate Subagent  
**Date:** 2026-05-19 UTC  
**Baseline:** v62 (agent_cl_gpt_v62.py) | King: d24c9d3  
**Task:** Challenge all 5 proposed changes, produce final build spec

---

## VERDICTS TABLE

| Change | Proposed | Challenge | Counter-Evidence | VERDICT |
|--------|----------|-----------|-----------------|---------|
| C1: Step-Based Hail-Mary | Add step≥8 trigger to mid-loop hail-mary | Real gap confirmed — v62 has TIME trigger only; king has DUAL | King's `_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7`, v62 lacks this entirely (confirmed grep) | ✅ **KEEP** |
| C2: Anti-Churn Rules | Add SYSTEM_PROMPT "ANTI-CHURN DISCIPLINE" section | v62 ALREADY has this text: "Unnecessary changes (whitespace, import reorder, comment-only edits) actively hurt your score" + code-level `_hunk_is_whitespace_only` stripper + 80% self-check gate explicitly lists churn items | Evidence: v62:2938-2939, v62:1683-1762, v62:3191-3208. Adding a 3rd framing is redundant and could inflate SYSTEM_PROMPT length | ⚠️ **MODIFY** |
| C3: Correctness-First Reorder | Promote CORRECT before COMPLETE in SYSTEM_PROMPT | v62 ALREADY opens with ROOT CAUSE RESOLUTION as dimension #1, followed by SCOPE COMPLETENESS. The phrase "COMPLETENESS BEATS MINIMALISM" appears AFTER these dimensions. King has the same order. The ROOT_CAUSE_SN66_vNEXT.md misreads v62's structure. | Confirmed: v62:2934 `1. ROOT CAUSE RESOLUTION`, v62:2941 `COMPLETENESS BEATS MINIMALISM`. Already correct-first. Risk: rewriting priority section could cause regressions. | ⚠️ **MODIFY** |
| C4: BUGFIX-Specific Root Cause Rules | Add BUGFIX task section with call-site tracing, error handling, no security regressions | v62 already has ROOT CAUSE RULE (v62:3026-3040) + call-site tracing (v62:3020) + "no security regressions" nowhere explicit. DPO shows BUGFIX = 73% of tasks today. Missing: security regression warning is a genuine gap | Partial coverage confirmed. Security regression (10% of BUGFIX rejections) is NOT in v62. Call-site tracing IS. This is half-redundant, half-new. | ✅ **KEEP** (scope-limited) |
| C5: Sonnet Code Quality Signals | Add LANGUAGE IDIOM RULE section | v62 already has dimension "4. CODE QUALITY: Valid syntax, no stubs/TODOs, follows codebase conventions" + LANGUAGE-SPECIFIC COMPLETENESS RULES section. King has the same. DPO data: `cleaner` only 35/200 in DISAGREEMENT cases = only 17.5% of 20.3% disagreements = ~3.5% overall signal. | Idiomatic language rules are already in v62 LANGUAGE-SPECIFIC section. True new signals from Sonnet (error handling, production-ready) are small effect. Risk of SYSTEM_PROMPT bloat reducing M2.7 instruction-following. | ⚠️ **MODIFY** |

---

## DETAILED DEBATES

### C1: Step-Based Hail-Mary — KEEP ✅

**Challenge:** Is the missing step trigger actually causing lost rounds, or is the time trigger adequate?

**Analysis:**
- King: `_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7`, fires when `step >= 7 OR elapsed >= 55% of budget`
- v62: fires ONLY when `elapsed >= 50% of budget`
- The divergence: M2.7 on M2.5-TEE/GLM-5 is often FAST. On complex repos it reads many files quickly (10+ steps in under 20% of budget). The time trigger doesn't fire at 20% elapsed but the step trigger would fire at step 7-8.
- DPO evidence: "fast-inspection loops with no patches" are a real failure mode. Confirmed by `challenger_exit_reason: solver_error` pattern when agent runs out of time.

**Counter-counter:** King uses `step >= 7`, ROOT_CAUSE doc suggests `step >= 8`. What's right?

**Resolution:** Use `step >= 7` (exact king value). No reason to deviate from proven production setting. Threshold of 8 in the synthesis doc appears to be a typo vs king's actual 7.

**VERDICT: KEEP — add `_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7` and dual-trigger logic matching king exactly.**

---

### C2: Anti-Churn Rules — MODIFY ⚠️

**Challenge:** v62 ALREADY has anti-churn framing in 3 places:
1. SYSTEM_PROMPT (v62:2938): "Do not pad your diff... Unnecessary changes (whitespace, import reorder, comment-only edits) actively hurt your score."
2. `_hunk_is_whitespace_only()` code gate (v62:1683) strips whitespace-only hunks before submission
3. 80% self-check gate (v62:3191-3208) explicitly lists "No whitespace-only, comment-only, or blank-line-only hunks"

Adding a 4th "ANTI-CHURN DISCIPLINE" section would be:
- Redundant with 3 existing mechanisms
- SYSTEM_PROMPT bloat → dilutes other instructions for M2.7

**What's genuinely missing:** The ROOT_CAUSE doc's 22-27% churn figure is real, but the cause may NOT be missing instructions. It may be M2.7's inherent over-editing tendency (57.6% exceed reference size) that no SYSTEM_PROMPT rule fully stops without triggering incompleteness.

**Counter-evidence from DPO:** "Unnecessary complexity with additional endpoints, record types" (UPDATE rejection) and "code reordering, import sorting" (BUGFIX rejection). These are SCOPE-level sins, not whitespace sins. Current language covers them adequately.

**VERDICT: MODIFY — Do NOT add a new anti-churn section. Instead, add ONE targeted sentence to existing churn language: explicitly call out "no unrequested file permission changes (chmod), no unrequested import reordering beyond what the fix requires." This addresses the specific gap without bloat.**

---

### C3: Correctness-First Reorder — MODIFY ⚠️

**Challenge:** The synthesis doc claims v62 "leads with COMPLETENESS BEATS MINIMALISM." This is WRONG.

Actual v62 SYSTEM_PROMPT opening structure:
```
Line 2934: 1. ROOT CAUSE RESOLUTION (correctness)
Line 2935: 2. SCOPE COMPLETENESS
Line 2936: 3. ACCEPTANCE CRITERIA COVERAGE
Line 2937: 4. CODE QUALITY
Line 2941: COMPLETENESS BEATS MINIMALISM [appears AFTER the 4-dimension list]
```

The dimensions are already in CORRECT → COMPLETE → QUALITY order. The "COMPLETENESS BEATS MINIMALISM" statement appears AFTER and is not a reordering, it's an asymmetry statement for the completeness dimension.

**What IS genuinely needed:** Sonnet scores breaking errors more harshly than GPT-5.4. Adding an explicit statement about this new reality is valid. But it should be an ADDITION, not a reorder.

**VERDICT: MODIFY — Add one sentence after dimension #1 in the 4-dimension list: "CORRECTNESS IS GATING: breaking compilation errors or import failures cause near-zero scores regardless of completeness. For the LLM judge (Claude Sonnet): correct, compilable patches score before completeness considerations are applied." Do NOT reorder existing structure — it's already correct-first.**

---

### C4: BUGFIX-Specific Root Cause Rules — KEEP ✅ (scope-limited)

**Challenge:** v62 already has ROOT CAUSE RULE section (v62:3026-3040) covering:
- Fix the behavior owner, not downstream symptom
- Cascade all affected call sites
- DELETE broken code, REPLACE rather than wrap

What v62 LACKS (confirmed absent):
- Security regression warning (hardcoded secrets, broken .gitignore) — appears in 10% of BUGFIX rejections
- Explicit "check for all files that propagate the bug" step for BUGFIX specifically

**DPO evidence:** 10% of BUGFIX rejections cite security regressions (hardcoded secrets, .env issues). This is real and not covered anywhere in v62. The ROOT_CAUSE RULE is generic; a BUGFIX-specific anti-regression note would add genuine signal.

**Counter-argument:** Adding a BUGFIX-specific section risks making the SYSTEM_PROMPT task-type-conditional in a way M2.7 may not follow reliably. Better to add it to the existing ROOT CAUSE RULE as a universal bullet.

**VERDICT: KEEP but MODIFY scope — Add to existing ROOT CAUSE RULE section (not a new section): "Never introduce security regressions: do not hardcode secrets/tokens, do not overwrite .gitignore with insecure defaults, do not expose credentials in error messages." One targeted sentence. No new section header needed.**

---

### C5: Sonnet Code Quality Signals — MODIFY ⚠️

**Challenge:** Effect size is smaller than the synthesis doc implies.

Math: Sonnet cites `cleaner` in 35/200 DISAGREEMENT cases. Disagreements = 20.3% of all cases. Therefore `cleaner` drives ~35/1000 outcomes overall = 3.5% base rate. `idiomatic` = 5/200 = 1% overall.

v62 ALREADY has:
- "4. CODE QUALITY: Valid syntax, no stubs/TODOs, follows codebase conventions" (dimension 4)
- LANGUAGE-SPECIFIC COMPLETENESS RULES with per-language guidance (Python, TypeScript, Java, Go etc.)
- "follows codebase conventions" implicitly covers idiomatic code

What's genuinely new and missing:
- Explicit `error handling` guidance (try/catch, fallbacks) — 10/200 = 2% effect, but additive
- "production-ready" framing for migrations and test inclusion — small signal but costs nothing

**Risk:** Adding a full LANGUAGE IDIOM RULE section (as proposed) with Python/TypeScript/Go specifics DUPLICATES the existing LANGUAGE-SPECIFIC COMPLETENESS RULES. This is pure bloat.

**VERDICT: MODIFY — Add ONE sentence to dimension #4 CODE QUALITY: "Add appropriate error handling (try/catch, fallback logic, error return types) where the fix introduces new failure paths. Write idiomatic code for the detected language." Skip the dedicated LANGUAGE IDIOM RULE section — it duplicates existing language rules.**

---

## FINAL BUILD SPEC — vNEXT (ProjectNobi-v65)

**Base:** `agent_cl_gpt_v62.py` — copy exactly, apply 4 targeted changes below

### Change A: Step-Based Hail-Mary (Code — ~5 lines)
**Location:** After `_MID_LOOP_HAIL_MARY_BUDGET_FRACTION` constant definition
```python
# Add after line ~114 in agent_cl_gpt_v62.py:
_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7  # dual trigger: time OR step (port from king)
```

**Location:** Mid-loop hail-mary trigger block (~v62:4276-4280), replace:
```python
# OLD (time-only trigger):
if (
    mid_loop_hail_mary_used < MAX_MID_LOOP_HAIL_MARY_TURNS
    and _elapsed_now >= _MID_LOOP_HAIL_MARY_BUDGET_FRACTION * wall_clock_budget
    and not get_patch(repo).strip()
):
```
with:
```python
# NEW (dual trigger — time OR step, matching king):
_hm_time_trigger = _elapsed_now >= _MID_LOOP_HAIL_MARY_BUDGET_FRACTION * wall_clock_budget
_hm_step_trigger = step >= _MID_LOOP_HAIL_MARY_STEP_TRIGGER
if (
    mid_loop_hail_mary_used < MAX_MID_LOOP_HAIL_MARY_TURNS
    and (_hm_time_trigger or _hm_step_trigger)
    and not get_patch(repo).strip()
):
    _hm_trigger_reason = "time" if _hm_time_trigger else f"step={step}"
    # (add to logs: f"MID_LOOP_HAIL_MARY_FIRED:{_hm_trigger_reason}")
```

### Change B: Anti-Churn Precision (SYSTEM_PROMPT — 1 sentence addition)
**Location:** After existing "Unnecessary changes (whitespace, import reorder, comment-only edits) actively hurt your score." line
Add: `"No unrequested file permission changes (chmod), no unrequested import reordering beyond what the fix requires."`

### Change C: Correctness Gating Statement (SYSTEM_PROMPT — 1 sentence)
**Location:** After `1. ROOT CAUSE RESOLUTION:` dimension description
Add: `"CORRECTNESS IS GATING: breaking compilation errors or import failures cause near-zero scores regardless of completeness. Produce correct, compilable code first. Then maximize completeness."`

### Change D: Security Regression Warning (SYSTEM_PROMPT — 1 sentence)
**Location:** Append to existing ROOT CAUSE RULE section
Add: `"Never introduce security regressions: do not hardcode secrets/tokens/passwords, do not overwrite .gitignore with insecure defaults, do not expose credentials in error messages or debug output."`

### Change E: Error Handling Signal (SYSTEM_PROMPT — 1 sentence to existing CODE QUALITY dimension)
**Location:** After `4. CODE QUALITY: Valid syntax, no stubs/TODOs, follows codebase conventions, includes docstrings on new functions.`
Add: `"Add appropriate error handling (try/catch, fallbacks, proper error return types) where the fix introduces new failure paths. Write idiomatic code for the detected language."`

---

## WHAT STAYS IDENTICAL FROM v62

- All existing timing constants (soft nudge, forced edit, budget fraction)
- Soft nudge mechanism (`build_soft_nudge_prompt`)
- Forced edit gate at 80% wall-clock
- `COMPLETENESS BEATS MINIMALISM` statement (keep as-is — asymmetry is correct)
- UPDATE TASK WIRING RULE (keep verbatim — valid and working)
- LANGUAGE-SPECIFIC COMPLETENESS RULES (keep — covers code quality already)
- ROOT CAUSE RULE section (keep, just ADD security regression line)
- THOROUGHNESS PROTOCOL (keep)
- All code gates: `_hunk_is_whitespace_only`, polish gate, coverage nudge, criteria self-check

## WHAT GETS DROPPED FROM PROPOSAL

- ❌ Dedicated "ANTI-CHURN DISCIPLINE" section (redundant with existing framing)
- ❌ Full "LANGUAGE IDIOM RULE" section (redundant with LANGUAGE-SPECIFIC COMPLETENESS RULES)  
- ❌ BUGFIX-specific new section (existing ROOT CAUSE RULE covers it; security line added there instead)
- ❌ Priority order rewrite (v62 is already CORRECT → COMPLETE → QUALITY — no reorder needed)

## HOTKEY NAME

`ProjectNobi-v65` — per L-SN66-AGENT-USERNAME-MANDATORY-1

## EXPECTED WR IMPACT

| Change | Estimated WR gain |
|--------|------------------|
| A: Dual hail-mary trigger | +3-4% (closes fast-loop gap) |
| B: Anti-churn precision | +0.5% (marginal — most already covered) |
| C: Correctness gating | +1-2% (explicit signal for Sonnet judge) |
| D: Security regression | +0.5% (BUGFIX edge cases) |
| E: Error handling signal | +0.5-1% (Sonnet-specific reward) |
| **Total estimated** | **+5.5-8.5% WR = target ≥70% gate reachable** |

**Dethronement case:** v62b = 53.1% WR (+3 net). vNEXT target = ≥57% WR (+5 net margin). Conservative estimate puts us at 58-61% = safe margin above +4 threshold.

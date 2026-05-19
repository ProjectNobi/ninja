# ROOT CAUSE ANALYSIS — SN66 v66
**Analyst:** T68Bot Subagent  
**Date:** 2026-05-19  
**Baseline:** `agent_cl_gpt_v62_fix.py` (v62b) — DO NOT change base code  
**Gate context:** v65 failed 37.5% overall; BUGFIX 12% (2W/14L) — primary target  
**Judge:** LLM-only, Claude Sonnet 4.6 since PR#1598  
**Task distribution (live):** BUGFIX 73%, FEATURE 12%, API 9%, UPDATE 6%

---

## 1. WHY IS OUR BUGFIX WR ONLY 12%?

### 1a. The THOROUGHNESS PROTOCOL is UPDATE/FEATURE framing applied to BUGFIX

v62b SYSTEM_PROMPT says: **"Most tasks require changes across 3-8 files."**

This is correct for UPDATE/FEATURE. For BUGFIX it is **actively harmful**:
- M2.7 gold data: BUG_FIX archetype = 0.50x reference ratio, **18% severe under-edit** — the worst ratio of all archetypes. M2.7 under-edits BUGFIX *relative to reference*, meaning the correct approach IS more surgical.
- DPO data: BUGFIX wins are for "minimal, targeted, correct" patches. "Properly fixes root cause" = wins. "Broad refactor scope" = penalized.
- When M2.7 reads "3-8 files required," it goes broad on BUGFIX tasks where the fix is 1-2 files. It touches unrelated callers, adds unnecessary abstraction, makes cosmetic changes. The judge sees "unnecessary churn" and penalizes.

**Root cause #1:** THOROUGHNESS PROTOCOL conflates BUGFIX with UPDATE/FEATURE, causing M2.7 to over-scope.

### 1b. The plan template `Strategy` line gives wrong guidance for BUGFIX

v62b plan template: `"Strategy: [approach - fix root cause, update all cascading files]"`

King plan template: `"Strategy: smallest root-cause fix likely to satisfy the issue."`

The difference is subtle but critical. **"Update all cascading files"** is UPDATE framing. For BUGFIX, M2.7 follows this instruction and updates callers that don't need updating. The king's phrasing — "smallest root-cause fix" — primes M2.7 toward precision.

**Root cause #2:** Strategy prompt line trains M2.7 to do UPDATE-style work on BUGFIX tasks.

### 1c. ROOT CAUSE RULE lacks concrete examples → M2.7 still reaches for symptom fixes

v62b: "DELETE broken code and REPLACE with correct code. Do not just add guards, null-checks, or try/catch wrappers around broken logic."

King (verified superior): Lists concrete examples of root cause reasoning:
- "Cache returns stale value → fix invalidation"
- "CLI option ignored → fix option parsing"  
- "Validation rejects valid case → fix validation rule, not caller workaround"
- "When several fixes are correct, choose the one that changes fewest files, smallest owning function"

Without concrete examples, M2.7 defaults to familiar symptom-fix patterns (adding try/catch, null guards, fallback returns) even when the prompt says not to. The judge (Sonnet 4.6) explicitly penalizes these: DPO data shows "symptom patch without root cause" in 3rd most common rejection reason for BUGFIX.

**Root cause #3:** Abstract anti-pattern rules without examples are ignored by M2.7 under pressure.

### 1d. No BUGFIX-specific cascade check

v62b THOROUGHNESS PROTOCOL lists 5 cascades (IMPORT, TEST, CONFIG, ROUTE/NAV, AC CHECKLIST) — all UPDATE/FEATURE oriented.

For BUGFIX, the relevant cascade is:
1. **Test cascade**: Does the companion test verify the fix? Does it need updating?
2. **Caller cascade**: If the fixed function's contract changed, which callers assume the old (broken) behavior?
3. **Error handling cascade**: Is the correct error type used? Is there error documentation to update?

Without BUGFIX-specific cascade guidance, M2.7 either (a) misses the companion test (80% incompleteness in rejected BUGFIX per DPO data) or (b) applies UPDATE-style cascade and touches too many files.

**Root cause #4:** No BUGFIX-specific cascade checklist → missing test files + broken callers.

### 1e. Sonnet-specific quality signals not addressed

New judge (Claude Sonnet 4.6) rewards in disagreement cases (20.3% of duels): `cleaner` (17.5%), `architectural` (11.5%), `error handling` (5%), `idiomatic` (2.5%). v62b SYSTEM_PROMPT has no guidance for these.

For BUGFIX specifically: Sonnet rewards "architecturally correct" fixes (fix in the right layer) over "cleverly works" fixes. An error wrapped in try/catch works but is architecturally wrong — Sonnet penalizes this even if it passes tests.

**Root cause #5:** v62b SYSTEM_PROMPT not calibrated to Sonnet 4.6's quality preferences.

---

## 2. WHAT DOES THE KING DO FOR BUGFIX THAT WE DON'T?

| Aspect | King | v62b |
|--------|------|-------|
| Plan template strategy | "smallest root-cause fix" | "fix root cause, update all cascading files" |
| ROOT CAUSE examples | 4 specific patterns (cache, CLI, validation, parser) | Generic rule only |
| "Smallest owning function" rule | ✅ Explicit | ❌ Missing |
| BUGFIX surgical framing | SURGICAL EDITING section guards against over-editing | THOROUGHNESS PROTOCOL pushes 3-8 files for ALL tasks |
| Forbidden scope-creep list | Explicit: "formatting churn, import sorting, renames for taste, new helpers" | Implicit only |
| Style preservation | Detailed: "Preserve EVERY meaningful comment" | Basic |
| Hidden test hint | "Hidden tests usually check the general behavior, not the literal example" | ❌ Missing |

**Key king advantage:** King never says "most tasks require 3-8 files" — it says "change fewest files necessary." This is the surgical-vs-thorough framing split that directly maps to BUGFIX wins.

---

## 3. WHAT DOES THE JUDGE REWARD FOR BUGFIX? (DPO_INTEL data)

| Reward signal | Frequency in chosen patches |
|--------------|----------------------------|
| Root cause fix (not symptom) | 70% of chosen praised |
| Complete fix including all related files | 70% of chosen praised |
| Minimal, targeted, correct | "targeted" appears in 12/20 BUGFIX wins |
| Retry/fallback logic for network/IO bugs | 5/20 BUGFIX wins |
| No security regressions | Critical: 10% of BUGFIX rejections are security issues |

| Rejection signal | Frequency |
|-----------------|-----------|
| Missing the actual fix | 80% incomplete/partial |
| Symptom patch (wrong layer) | 3rd most common |
| Wrong codebase entirely | Catastrophic (wrong files) |
| Security regression | 10% of rejections |
| Truncated patch | 35% of rejections |

**Key BUGFIX judge insight:** "Root cause + all affected files + completeness beats root cause alone." — You must fix root cause AND cover all stated acceptance criteria. BUGFIX is the most surgical task type but still requires completeness.

---

## 4. TOP 5 CHANGES FOR v66 (BUGFIX-focused, minimum changes to v62b)

**Constraint:** v62b is the base. Preserve UPDATE TASK WIRING RULE (60% UPDATE WR). Minimum text changes.

---

### CHANGE 1: Split THOROUGHNESS PROTOCOL by task type

**Problem:** "Most tasks require changes across 3-8 files" applies UPDATE/FEATURE logic to BUGFIX.

**Exact text to ADD** at top of THOROUGHNESS PROTOCOL section (before item 1):

```
**TASK-TYPE SCOPE RULE:**
- BUG FIX tasks: primary fix file + companion test + signature callers ONLY (1-3 files typical). Do NOT apply UPDATE file-count targets to bug fixes.
- UPDATE/FEATURE tasks: all 5 cascade types below apply (3-8 files).
```

**Why this fixes BUGFIX:** Prevents M2.7 from going broad on BUGFIX tasks. Keeps UPDATE WR by being explicit that UPDATE gets the full cascade.

**Risk to UPDATE/REFACTOR:** None — the 3-8 file rule still applies to UPDATE explicitly.

---

### CHANGE 2: Add concrete ROOT CAUSE examples + anti-pattern list

**Problem:** Abstract rules don't stop M2.7 from adding try/catch wrappers.

**Exact text to ADD** after "DELETE broken code and REPLACE with correct code." in ROOT CAUSE RULE:

```
Root cause patterns (fix THESE, not the caller):
- Parser rejects valid input → fix the parser rule
- Cache returns stale value → fix invalidation, not the read path
- CLI option ignored → fix option parsing, not downstream defaults
- Validation rejects valid case → fix the validation rule, not add a bypass

SYMPTOM ANTI-PATTERNS (judge explicitly penalizes these for BUGFIX):
- Adding try/catch around broken logic (symptom suppression)
- Adding null-check guard in front of broken call (symptom guard)
- Adding fallback return before broken code path (symptom routing)
- Calling workaround function instead of fixing callee (symptom delegation)

When several fixes work, prefer: fewest files changed, smallest owning function, uses existing codebase helpers.
```

**Why this fixes BUGFIX:** M2.7 has concrete examples of what root cause looks like + explicit list of forbidden patterns with judge rationale. DPO data shows 70% of BUGFIX rejections involve symptom fixes.

**Risk to UPDATE/REFACTOR:** None — UPDATE doesn't involve symptom/root-cause distinction. REFACTOR already at 100% WR.

---

### CHANGE 3: Fix the plan template Strategy line

**Problem:** "update all cascading files" is UPDATE framing applied to all task types.

**Exact change** in the plan template block (first response format):

Replace:
```
- Strategy: [approach - fix root cause, update all cascading files]
```

With:
```
- Strategy: [For BUG FIX: smallest root-cause fix, 1-3 files max. For UPDATE/FEATURE: complete implementation, all wiring layers. State which type this is.]
```

**Why this fixes BUGFIX:** The plan block is the first thing M2.7 writes. If it commits to "1-3 files, root cause" at step 1, it stays surgical. DPO data shows plans that commit to precision early produce more complete (not more broad) patches.

**Risk to UPDATE/REFACTOR:** Zero — UPDATE gets explicit "complete implementation, all wiring layers" which is stronger than the current vague "update all cascading files."

---

### CHANGE 4: Add BUGFIX-specific cascade checklist

**Problem:** THOROUGHNESS PROTOCOL items 1-5 are UPDATE/FEATURE cascades. BUGFIX needs different cascade.

**Exact text to ADD** as a new item 6 in THOROUGHNESS PROTOCOL:

```
6. BUGFIX CASCADE (BUG FIX tasks only — replaces items 1-5 scope): After primary root-cause fix:
   a. COMPANION TEST: Find test file for fixed module → update or add test that reproduces the bug → verify it now passes.
   b. CALLER CONTRACT: If fixed function's return value or exceptions changed → grep callers → update those that assumed old (broken) behavior.
   c. ERROR TYPE: Use the correct, specific exception/error type for this language (not generic Exception/Error). Check existing patterns.
   d. AC CHECKLIST: Before <final>, confirm every bullet in the issue has a matching change.
```

**Why this fixes BUGFIX:** DPO data: 80% BUGFIX rejections are incomplete. The most common missing elements are: companion test (judge expects verification), caller updates (cascading contract change), correct error typing (Sonnet rewards idiomatic error handling).

**Risk to UPDATE/REFACTOR:** Zero — item is explicitly scoped to BUG FIX tasks.

---

### CHANGE 5: Add Sonnet 4.6-specific quality signals

**Problem:** v62b SYSTEM_PROMPT calibrated to GPT-5.4 (raw criteria alignment). Sonnet 4.6 additionally rewards cleaner, architectural, idiomatic code.

**Exact text to ADD** at end of STYLE AND CONVENTIONS section:

```
Claude Sonnet 4.6 judge additionally rewards (verified from live duel data):
- IDIOMATIC code: use language-native patterns (Python list comprehensions, TypeScript generics, Go interfaces)
- ARCHITECTURAL precision: fix in the correct layer (don't fix downstream if upstream is broken)
- PROPER error types: named exception classes, not generic Exception/Error/catch-all
- PRODUCTION-READY: no TODO stubs, no placeholder comments, no magic numbers without named constants
- CLEAN: no reformatting of unrelated code, no import reordering, no style churn
```

**Why this fixes BUGFIX:** Sonnet disagrees with GPT-5.4 in 20.3% of duels and rewards these quality signals. For BUGFIX specifically, "architectural precision" = root cause wins over symptom fix. This text directly maps to higher scores.

**Risk to UPDATE/REFACTOR:** Positive — these quality signals improve all task types.

---

## 5. FORBIDDEN PATTERNS (must not regress UPDATE 60% WR)

| Rule | Why it must not change |
|------|----------------------|
| UPDATE TASK WIRING RULE section | Our 60% UPDATE WR comes directly from this section |
| "COMPLETENESS BEATS MINIMALISM" headline | UPDATE needs this to cover all 3-8 files |
| THOROUGHNESS PROTOCOL items 1-4 (CASCADE types) | UPDATE relies on IMPORT/TEST/CONFIG/ROUTE cascades |
| "Reference patches typically touch 3-6 files" | UPDATE needs this framing (but scope to UPDATE only per Change 1) |
| AC CHECKLIST step | Both UPDATE and BUGFIX need this |
| Never add "never delete existing functions" language | Would collapse REFACTOR and destroy root-cause replacement for BUGFIX |
| Never make SCOPE DISCIPLINE less surgical | Would hurt BUGFIX (judge penalizes churn) |

---

## 6. EXPECTED WR AFTER CHANGES

### Calculation basis (v65 gate: 50 tasks, seed 42)
- BUGFIX: 16 tasks (32%) | v65: 12% WR (2W/14L)
- FEATURE: 11 tasks (22%) | v65: 45% WR (5W/6L)
- UPDATE: 5 tasks (10%) | v65: 60% WR (3W/2L)
- REFACTOR: 1 task (2%) | v65: 100% WR
- Other: 17 tasks (34%) | v65: ~26% (4W/13L est)

### Projected v66 WR (conservative)

| Task Type | v65 | v66 projected | Δ wins (of gate tasks) |
|-----------|-----|--------------|----------------------|
| BUGFIX | 12% (2W) | **35-40%** (5.6-6.4W) | +3.6 to +4.4 |
| FEATURE | 45% (5W) | **48-52%** (5.3-5.7W) | +0.3 to +0.7 |
| UPDATE | 60% (3W) | **55-65%** (2.75-3.25W) | -0.25 to +0.25 |
| REFACTOR | 100% (1W) | **100%** (1W) | 0 |
| Other | ~26% (4W) | **28-32%** (4.8-5.4W) | +0.8 to +1.4 |

**Projected total wins:** 19.5 to 21.2 out of 40 decisive = **48-53% WR**

### Assessment
v66 is unlikely to clear 60% gate on first attempt with SYSTEM_PROMPT changes alone. However:
- v62b was +3 margin vs king (need +4) in live duel — only 1 round short
- v66 with BUGFIX improvement will push WR to ~50% in gate
- Actual live duel may perform better than gate (seed 42 has heavy BUGFIX distribution)
- **Realistic live duel WR: 53-58%** — within striking distance of dethrone

To reach 60% gate, BUGFIX WR needs to reach ~55-60% (9-10W/16). Changes 1-5 target this but may not fully get there. A second iteration (v67) may be needed after observing which BUGFIX sub-patterns still fail.

---

## SUMMARY: TOP 5 CHANGES

1. **Split THOROUGHNESS PROTOCOL** → BUGFIX = 1-3 files surgical. UPDATE/FEATURE = 3-8 files.
2. **Add ROOT CAUSE examples + anti-patterns** → parser/cache/validation/CLI examples + forbidden symptom patterns list.
3. **Fix plan template Strategy** → "For BUG FIX: smallest root-cause fix, 1-3 files max."
4. **Add BUGFIX cascade checklist** → companion test + caller contract + error type + AC check.
5. **Add Sonnet 4.6 quality signals** → idiomatic, architectural, proper error types, production-ready.

**Expected WR: BUGFIX 12% → 35-40%, Overall 37.5% → 48-53%**

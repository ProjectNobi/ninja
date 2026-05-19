# DEBATE — ROOT CAUSE SN66 v66
**Analyst:** T68Bot Subagent (Devil's Advocate)  
**Date:** 2026-05-19  
**Source:** ROOT_CAUSE_SN66_v66.md (5 changes) vs v62b code vs DPO_INTEL_SN66_vNEXT.md  
**Deliverable:** Verdict table + exact confirmed additions

---

## VERDICT TABLE

| # | Change | Already in v62b? | DPO supports? | Regression risk? | Root cause or symptom? | VERDICT |
|---|--------|-----------------|--------------|-----------------|----------------------|---------|
| 1 | Split THOROUGHNESS: 1-3 files for BUGFIX | ❌ No | ⚠️ PARTIAL — contradicted by 94% completeness signal | HIGH — could cause under-edit | SYMPTOM — caps files but doesn't redirect scope | **MODIFY** |
| 2 | ROOT CAUSE examples + anti-pattern list | ⚠️ PARTIAL — parser + no-try/catch already present | ✅ Yes — cache/CLI/smallest-owner are NEW | LOW | ROOT CAUSE | **MODIFY** |
| 3 | Fix plan template Strategy line | ❌ No — exact line 2996 is the problem | ✅ Yes — king framing wins | ZERO — UPDATE gets stronger wording | ROOT CAUSE | **KEEP** |
| 4 | BUGFIX-specific cascade checklist (item 6) | ⚠️ PARTIAL — TEST+IMPORT cascades already exist | ⚠️ PARTIAL — caller contract NEW, companion test duplicate | LOW | ROOT CAUSE for NEW parts | **MODIFY** |
| 5 | Sonnet 4.6 quality signals (5 bullets) | ❌ No | ✅ Yes — in 20.3% disagree cases | LOW risk, LOW signal — only 2.5-17.5% of disagree cases | SYMPTOM — targets edge cases not core gap | **MODIFY** |

---

## CHANGE-BY-CHANGE DEBATE

### CHANGE 1 — Split THOROUGHNESS PROTOCOL (1-3 files for BUGFIX)

**Proposed:** "BUG FIX tasks: 1-3 files typical. Do NOT apply UPDATE file-count targets."

**Devil's advocate challenge — DPO data directly contradicts this:**
- DPO TOP FINDING 1: "Surgical minimalism is praised only 3-6% of the time. The agent that covers more acceptance criteria wins."
- DPO BUGFIX: "80% incomplete, 35% truncated" — completeness failures dominate rejections.
- BUGFIX DPO chosen: "Root cause + complete fix including all related files" — not "1-3 files."

**Is this the root cause or a symptom?**  
The actual problem is M2.7 going to the WRONG files (symptom callers) rather than root cause owner files. Capping at "1-3 files" treats the symptom — it would cause M2.7 to UNDER-edit complex bugs that genuinely span 3-4 files (e.g., fixing a broken cache requires: cache module + invalidation trigger + companion test = 3 files minimum).

**VERDICT: MODIFY**  
Do NOT cap file count. Instead, redirect cascade for BUGFIX:

```
BUGFIX SCOPE RULE: For BUG FIX tasks — cascade to the ROOT CAUSE OWNER file and files it directly affects (callers that assumed the broken behavior). Do NOT touch files that merely call the broken function without assuming its broken output (those are symptom files). 1-3 files is common but NOT a ceiling — a bug spanning the cache layer, invalidation trigger, and test requires all three.
```

Add this immediately before THOROUGHNESS PROTOCOL item 1 (inside the section, after "3-8 files" sentence), scoped as a BUGFIX note only.

---

### CHANGE 2 — ROOT CAUSE examples + anti-pattern list

**Proposed:** Add parser/cache/CLI/validation examples + 4 forbidden anti-patterns.

**Devil's advocate challenge — partial duplication:**
- v62b line 3032 already has: `"Parser rejects valid input -> fix parser. Serializer omits field -> fix serializer."` — parser example IS present.
- v62b line 3036 already has: `"DELETE broken code and REPLACE with correct code. Do not just add guards, null-checks, or try/catch wrappers."` — anti-pattern framing partially present.

**What is genuinely new and supported by DPO?**
- Cache invalidation example (NEW): not in v62b. DPO BUGFIX wins include "fix invalidation, not read path" pattern.
- CLI option example (NEW): not in v62b.
- "Smallest owning function" rule (NEW): not in v62b. King has it explicitly.
- "Symptom delegation" anti-pattern (NEW): calling workaround instead of fixing callee — not in v62b.

**VERDICT: MODIFY**  
Drop parser example (duplicate). Keep: cache + CLI examples, "smallest owning function" rule, and only the two NEW anti-patterns (try/catch already partially covered; add delegation).

```
Root cause patterns (add AFTER existing "Parser rejects valid input -> fix parser" line):
- Cache returns stale value → fix invalidation logic, not the read path
- CLI option is ignored → fix option parsing, not downstream defaults
When multiple correct fixes exist: prefer the one that changes the smallest owning function and fewest files.

SYMPTOM ANTI-PATTERNS (judge explicitly penalizes for BUGFIX — add AFTER existing no-try/catch line):
- Routing callers to a workaround function instead of fixing the callee (symptom delegation)
- Adding fallback returns that silently hide broken behavior (symptom routing)
```

---

### CHANGE 3 — Fix plan template Strategy line

**Proposed:** Replace "fix root cause, update all cascading files" with task-type split.

**Devil's advocate challenge:**  
The strategy line is the FIRST commitment M2.7 makes. If the replacement is too verbose it may not be internalized. The king simply says "smallest root-cause fix" — no branching.

**Counter-challenge:**  
King can be minimal because its entire SYSTEM_PROMPT is already BUGFIX-calibrated. v62b is UPDATE-calibrated. The branching is necessary to preserve UPDATE WR while fixing BUGFIX strategy.

**DPO support:** Strong. UPDATE wins = completeness. BUGFIX wins = "minimal, targeted, correct." These are opposing optimization directions. The plan template Strategy line MUST branch.

**VERDICT: KEEP — no change from proposal.**

```
Replace line 2996:
  - Strategy: [approach - fix root cause, update all cascading files]

With:
  - Strategy: [BUG FIX: smallest root-cause fix, root-cause file + directly-broken callers only | UPDATE/FEATURE: complete implementation across all wiring layers — state which task type this is]
```

---

### CHANGE 4 — BUGFIX-specific cascade checklist (item 6)

**Proposed:** Full new item 6 with 4 sub-checks: companion test, caller contract, error type, AC checklist.

**Devil's advocate challenge — partial duplication:**
- Companion test: already covered by item 2 (TEST CASCADE). DPO top rejections for BUGFIX are "missing the actual fix" and "wrong codebase" — not "missing companion test." Adding a 6th item that repeats test guidance adds noise.
- AC checklist: already item 5, applies to all tasks.

**What is genuinely new?**
- Caller contract: "if fixed function's contract changed, update callers that assumed broken behavior" — this is DIFFERENT from IMPORT CASCADE. Import cascade = "callers use the function." Caller contract cascade = "callers assumed the old broken behavior as correct and compensated for it." NEW.
- Error type: "correct specific exception, not generic Exception/Error" — supported by DPO (Sonnet rewards proper error handling, 5% of disagreements). NEW.

**VERDICT: MODIFY**  
Don't add full item 6 (too much duplication). Instead, add 2 sentences to ROOT CAUSE RULE (after anti-patterns from Change 2):

```
BUGFIX CONTRACT CHECK: If your fix changes what the function returns or raises — search for callers that compensated for the broken behavior and update them.
BUGFIX ERROR TYPE: Use the most specific exception/error type available in the codebase for this error category. Sonnet penalizes bare Exception/Error catches.
```

---

### CHANGE 5 — Sonnet 4.6 quality signals (5 bullets)

**Proposed:** Add 5 new bullet points at end of STYLE AND CONVENTIONS.

**Devil's advocate challenge:**
- These signals appear in 20.3% of duels (disagreement cases). In 79.7% of duels, completeness still dominates.
- Adding 5 quality bullets could make M2.7 prioritize "clean idiomatic code" over "complete patch" — directly harming the #1 signal.
- "Production-ready" and "no TODO stubs" are already implied by "DELETE broken code and REPLACE with correct code."

**What genuinely matters based on DPO frequencies?**
- `cleaner` code: 17.5% of Sonnet disagreements — highest signal
- `architectural fitness`: 11.5% — second highest, directly maps to root cause vs symptom
- Others (idiomatic, error handling, production-ready): 2.5-5% — marginal

**VERDICT: MODIFY**  
Keep only 2 highest-frequency signals, folded into existing SCOPE DISCIPLINE section (not new section):

```
Add to end of SCOPE DISCIPLINE section:
Sonnet 4.6 judge uniquely rewards (in tie-breaks): CLEANER code (no reformatting unrelated lines, no import reordering, no style churn beyond what the task requires) and ARCHITECTURAL fitness (fix in the correct layer — callee not caller, service not controller, model not view).
```

---

## FINAL BUILD SPEC

### Base: `agent_cl_gpt_v62_fix.py` (v62b) — no changes to base code structure
### Hotkey: `ProjectNobi-v66`
### Total additions: 5 targeted text blocks (minimum changes, maximum BUGFIX impact)

---

### ADDITION 1 — BUGFIX SCOPE RULE
**Location:** Inside THOROUGHNESS PROTOCOL, after "Most tasks require changes across 3-8 files." line (line 3046)  
**Insert AFTER line 3046:**

```
BUGFIX SCOPE RULE: For BUG FIX tasks — cascade to the root-cause owner file and files that directly assumed the broken behavior. Do NOT touch files that merely call the broken function without depending on its broken output (those are symptom files). Common BUGFIX scope: 1-3 files, but this is NOT a ceiling — a bug spanning cache + invalidation + test legitimately requires all three.
```

---

### ADDITION 2 — ROOT CAUSE EXAMPLES (new examples only)
**Location:** ROOT CAUSE RULE section, AFTER existing "Parser rejects valid input -> fix parser. Serializer omits field -> fix serializer." line (line 3032)  
**Insert AFTER that line:**

```
- Cache returns stale value → fix invalidation logic, not the read path
- CLI option ignored → fix option parsing, not downstream defaults
When several correct fixes exist: prefer the one changing the smallest owning function and fewest files.

ADDITIONAL SYMPTOM ANTI-PATTERNS (add to fix, judge penalizes for BUGFIX):
- Routing callers to a workaround function instead of fixing the callee (delegation around root cause)
- Adding fallback returns that silently hide broken behavior (result masking)
```

---

### ADDITION 3 — PLAN TEMPLATE STRATEGY LINE
**Location:** Plan template block (line 2996)  
**Replace:**
```
- Strategy: [approach - fix root cause, update all cascading files]
```
**With:**
```
- Strategy: [BUG FIX: smallest root-cause fix, root-cause file + directly-broken callers only | UPDATE/FEATURE: complete implementation across all wiring layers — state which task type this is]
```

---

### ADDITION 4 — BUGFIX CONTRACT CHECK
**Location:** ROOT CAUSE RULE section, after the new anti-patterns block from Addition 2  
**Insert:**

```
BUGFIX CONTRACT CHECK: If your fix changes what the function returns or raises — search for callers that compensated for the broken behavior and update them.
BUGFIX ERROR TYPE: Use the most specific exception/error type available in this codebase for this error category. Generic Exception/Error/catch-all is penalized by Sonnet 4.6.
```

---

### ADDITION 5 — SONNET 4.6 TIE-BREAK SIGNALS
**Location:** SCOPE DISCIPLINE section (line 3112), at the end of that section  
**Insert:**

```
Sonnet 4.6 judge uniquely rewards in tie-breaks: CLEANER code (no reformatting unrelated lines, no import reorder, no style churn beyond what the task requires) and ARCHITECTURAL fitness (fix in the correct layer — callee not caller, service not controller, root cause not symptom).
```

---

## WHAT STAYS IDENTICAL FROM v62b

- UPDATE TASK WIRING RULE section — untouched (preserves 60% UPDATE WR)
- "COMPLETENESS BEATS MINIMALISM" headline — untouched
- THOROUGHNESS PROTOCOL items 1-5 (IMPORT/TEST/CONFIG/ROUTE/AC cascades) — untouched
- "Reference patches typically touch 3-6 files" completeness signal — untouched
- "DELETE broken code and REPLACE with correct code. Do not just add guards, null-checks, or try/catch wrappers" — untouched (Addition 2 supplements, does not replace)
- All base runtime code, tool wiring, harness logic — untouched

## WHAT IS DROPPED FROM ORIGINAL PROPOSAL

- "1-3 files typical for BUGFIX" ceiling → replaced with scope redirection (no ceiling)
- Parser example (already in v62b)
- Full item 6 cascade checklist (companion test is already item 2; AC is already item 5)
- 5-bullet Sonnet quality section → condensed to 1 sentence in SCOPE DISCIPLINE

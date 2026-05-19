# AUDIT + DEBATE — SN66 agent_cl_gpt_v69.py
*Auditor: T68Bot (second Opus instance) | 2026-05-19 13:34 UTC*

## Summary of Change
v69 replaces one line (`**FEATURE and UPDATE tasks:** enumerate ALL deliverables as checklist`) with a full **LARGE TASK COMPLETENESS PROTOCOL** block (21 lines) covering:
1. LARGE TASK DETECTION — wider `find` scan on tasks referencing >5 files
2. TIME BUDGET DISCIPLINE — stop exploring after 4+ inspection commands
3. UPDATE/ENHANCE TASKS — build complete feature, "include file rather than skip it"

Root cause targets: 35 big losses (ch_lines 17× below king), 13 timeouts, 14% UPDATE win rate.

---

## STEP 3: DEBATE — Root Cause Challenges

### Challenge 1: Does LARGE TASK DETECTION fix under-editing, or cause more exploration time?

**Finding:** Root cause is confirmed real — task 064730 (ch=455 vs k=7720, gap=0.70), 064694 (ch=0 vs k=7047), 064706 (ch=1238 vs k=8450). These are large FEATURE_BUILD tasks. Under-editing is the verified #1 failure mode.

**Challenge:** The DETECTION rule adds a `find` command BEFORE any code. On tasks with 13 timeouts already, any added exploration step risks pushing more tasks into timeout.

**Data resolution:** DUEL_ANALYSIS shows timeout tasks and under-editing tasks heavily overlap (task 064811 = both: timeout + ch_lines 3982 vs king 6922). The real problem is "agent explores single file, then runs out of time writing an incomplete patch." Adding explicit scope enumeration + committing partial work on time-limited tasks addresses BOTH root causes simultaneously.

**Verdict: KEEP.** The detection logic is sound IF the time budget discipline prevents over-exploration.

---

### Challenge 2: Is "4+ inspection commands" the right threshold?

**Finding:** King's runtime code (`agent_cl_gpt_v69.py:120`) has `_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7`. King halts at 7 inspection steps. v69 SYSTEM_PROMPT says halt at 4.

**Data:** The king built its hail-mary trigger around 7 because on typical R2 tasks, understanding a multi-file feature legitimately requires reading: task file, main source file, related module, test file, config — that's already 4-5 reads BEFORE writing. Stopping at 4 may force writing before the agent has read the target file.

**Evidence:** v68 gate UPDATE WR=14%. v68 was NOT over-exploring — it was under-exploring (missed cascade files). Forcing earlier code-writing would not fix this; it would worsen it.

**Verdict: NEEDS FIX.** Change to "6+ inspection commands" to align with king's proven step trigger of 7, OR update runtime `_MID_LOOP_HAIL_MARY_STEP_TRIGGER` from 7 → 4 in v69 code for consistency. Recommend: raise SYSTEM_PROMPT threshold to 6.

---

### Challenge 3: "When uncertain, include the file" — does this hurt BUGFIX precision?

**Finding:** BUGFIX is our best performing task type (gate WR 65%). BUGFIX requires surgical precision: smallest correct change, fewest files. The UPDATE rule "include file rather than skip it" is labeled under UPDATE/ENHANCE section but LLMs apply behavioral patterns across task types.

**Risk:** If the model generalizes "when uncertain, include" to BUGFIX tasks, scope creep appears: extra files added, extra hunks, SCOPE score drops.

**Data check:** v68 BUGFIX WR was 65% in gate. The v68 baseline had only the single-line rule ("enumerate ALL deliverables as checklist") — no aggressive inclusion rule. Adding a forceful "include rather than skip" could bleed into BUGFIX behavior.

**Verdict: MEDIUM RISK. Requires explicit guard.** Add: "This inclusion rule applies ONLY to UPDATE/ENHANCE tasks. For BUGFIX tasks, maintain surgical precision — smallest correct change."

---

### Challenge 4: Does v69 risk regressing BUGFIX WR while fixing UPDATE WR?

**Summary:** UPDATE fix mechanism (more files included) is in tension with BUGFIX success pattern (precision). The separation is only via section header — not a hard conditional in code.

**Verdict: REAL RISK, manageable.** Explicit guard (Challenge 3) is required. Without it, there's meaningful risk of BUGFIX regression offsetting UPDATE gains. Gate test should track task-type-specific win rates.

---

### Challenge 5: Does SYSTEM_PROMPT fix a model-level under-editing problem?

**Data:** M2.7 50% under-edit rate at model level (median patch/ref ratio = 0.70). King (using same M2.7) achieves full-feature output on large tasks. King's SYSTEM_PROMPT IS the mechanism — it provides explicit multi-file expansion rules, Dart/Flutter screen enumeration, integration cascade rules.

**Verdict: SYSTEM_PROMPT IS the right lever.** King proves it works on M2.7 via explicit completeness rules. v69's approach is correct in principle.

---

## STEP 4: AUDIT — Specific Issues

### ❌ Issue 1 (HIGH): `find` command operator precedence bug
**Location:** `agent_cl_gpt_v69.py:2972-2973` (LARGE TASK DETECTION block)

```bash
find . -type f -name "*.py" -o -name "*.ts" -o -name "*.dart" | head -80
```

**Bug:** `-type f` only applies to `*.py` due to operator precedence. Parsed as:
`(-type f AND -name "*.py") OR (-name "*.ts") OR (-name "*.dart")`

`*.ts` and `*.dart` patterns have no `-type f` constraint → directories with those extensions would match (rare but wrong).

**Fix:**
```bash
find . \( -name "*.py" -o -name "*.ts" -o -name "*.dart" \) -type f | head -80
```

---

### ❌ Issue 2 (HIGH): "4+ inspection commands" contradicts runtime step trigger of 7
**Location:** `agent_cl_gpt_v69.py:2977-2978` (TIME BUDGET DISCIPLINE) vs `agent_cl_gpt_v69.py:120` (runtime `_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7`)

SYSTEM_PROMPT instructs model to stop at 4 commands. Runtime code enforces hail-mary at step 7. Model receives contradictory signals: "stop at 4" vs environment behavior kicking in at 7. This creates mid-execution dissonance.

**Fix Option A:** Change SYSTEM_PROMPT to "6+ inspection commands" (closer to 7).
**Fix Option B:** Change `_MID_LOOP_HAIL_MARY_STEP_TRIGGER = 7` → `= 5` in code to align with SYSTEM_PROMPT intent.

Recommend Option A — keep runtime trigger at 7 (king-proven value), raise SYSTEM_PROMPT threshold to 6.

---

### ❌ Issue 3 (HIGH): UPDATE "include rather than skip" conflicts with SCOPE DISCIPLINE
**Location:** v69:2989 ("When uncertain whether a file needs changing: include it rather than skip it") vs v69:2992 SCOPE DISCIPLINE ("Do not broaden the patch beyond the task's behaviour")

These are direct contradictions with no conditional resolution. Model must choose between them on ambiguous cases.

**Fix:** Add explicit task-type guard in UPDATE section:
```
5. When uncertain whether a file needs changing: include it rather than skip it.
   ⚠️ This rule applies ONLY to UPDATE/ENHANCE tasks. For BUGFIX tasks, default to SCOPE DISCIPLINE (smallest correct change).
```

---

### ⚠️ Issue 4 (MEDIUM): Missing completeness asymmetry statement
**Location:** Should be in SYSTEM_PROMPT, between LANGUAGE-SPECIFIC COMPLETENESS RULES and SCOPE DISCIPLINE.

AGENTS.md (SN66 Forbidden Rules) states:
> ✅ REQUIRED — Completeness Asymmetry Rule: ALWAYS include "COMPLETENESS BEATS MINIMALISM. Missing files/requirements costs far more than extra thorough edits. Under-editing (missing a cascade file) is penalized MORE than slight over-editing."

Neither v69 nor king has this phrase verbatim. King achieves the same effect through its integration cascade rules and Dart/Flutter screen enumeration. v69 partially covers this via the UPDATE task rule. But the explicit asymmetry statement is missing.

**Fix:** Add after LANGUAGE-SPECIFIC COMPLETENESS RULES section:
```
COMPLETENESS BEATS MINIMALISM. Missing files/requirements costs far more than extra thorough edits. Under-editing (missing a cascade file) is penalized MORE than slight over-editing. When in doubt: include the file.
```
*(Applicable to all task types, unlike the UPDATE-specific rule.)*

---

### ✅ No Forbidden Patterns Found
Checked for all AGENTS.md forbidden patterns:
- "Never delete or remove existing functions" — NOT present ✅
- "Preserve existing code structure" — NOT present ✅
- "Only add, never remove" — NOT present ✅
- Pure minimalism framing without asymmetry — present implicitly through SCOPE DISCIPLINE, partially mitigated by LANGUAGE-SPECIFIC COMPLETENESS RULES ✅

---

### ✅ LARGE TASK DETECTION logic is sound
King does NOT have a LARGE TASK COMPLETENESS PROTOCOL section — king handles this via the runtime step trigger (7 commands) + Dart/Flutter screen enumeration rules. v69 provides SYSTEM_PROMPT-level guidance that mirrors king's runtime behavior. The concept is correct.

---

## Required Fixes Before Gate

| Priority | Fix | Location |
|----------|-----|----------|
| HIGH | Fix `find` command: add `\( ... \)` parentheses grouping | v69:2972 |
| HIGH | Raise TIME BUDGET threshold from "4+" to "6+" | v69:2977 |
| HIGH | Add UPDATE-only guard on "include rather than skip" rule | v69:2989 |
| MEDIUM | Add explicit completeness asymmetry statement | After line ~2951 |

---

## Verdict: NEEDS_CHANGES

v69 addresses the RIGHT root causes (timeout + under-editing + UPDATE WR). The architectural direction is sound. Three HIGH issues must be fixed before the 100-task gate:

1. `find` command produces wrong results (dirs with .ts/.dart extensions included)
2. "4 commands" threshold conflicts with runtime step trigger (7), risks premature code-writing that worsens timeout + under-editing — the opposite of the goal
3. UPDATE "include rather than skip" without BUGFIX guard risks regressing our best-performing task type (65% WR)

Fixing all three + adding completeness asymmetry gives v69 a clean path to gate pass. The core strategy is correct — needs precision tuning, not architectural rework.

**Estimated gate impact after fixes: UPDATE WR +20-30pp (from 14%), BUGFIX maintained at ~65%, timeout losses -30-40% on large feature tasks.**

# Root Cause Analysis — SN66 vNext (2026-05-19)

**Author:** Opus 4.7 Subagent (Step 3 — Synthesis + Root Cause)
**Date:** 2026-05-19 UTC
**Inputs:** SOURCE_INTEL_SN66_vNEXT.md (Step 1) + DATA_INTEL_SN66_vNEXT.md (Step 2)
**King:** d24c9d30 (4595L, private submission)
**v71 gate result:** 47% WR (34/100 tasks) — BELOW threshold (≥70%)

---

## Why v71 Is at 47% WR

### Root Cause 1: Missing Runtime Completeness Enforcement — The Structural Gap
**The single root cause tying ALL failures together:**

The king enforces completeness through **runtime mechanisms**. We rely on **prompting alone**. This is the structural gap.

King's runtime mechanisms (Step 1):
- `_uncovered_required_paths()` — detects files the issue implies but the patch doesn't touch → triggers `coverage_nudge` refinement turn
- `_solve_emergency_single_shot` — fires when budget < 60s, prevents empty patches entirely
- `MAX_TOTAL_REFINEMENT_TURNS = 3` with typed gates (hail-mary → syntax → test → deletion → coverage → criteria → polish → self-check)

Our v71 runtime mechanisms: **None.** We added rules to SYSTEM_PROMPT (correct direction) but did not port the king's enforcement loops.

**Evidence:**
- Step 1: King has `_solve_emergency_single_shot` at ~line 3556. All v62–v71 are missing this.
- Step 2: 3,058 "truncated" + 1,775 "incomplete" in UPDATE/FEATURE losses — the judge is seeing truncated patches because we run out of time with no fallback.
- Step 1: King's `coverage_nudge` refinement catches files that "the issue implies but patch doesn't touch" — we have no equivalent.

**Expected WR impact if fixed: +12–18%** (prevents every empty-patch loss + catches uncovered files)

---

### Root Cause 2: M2.7 Truncates Under Time Pressure — Anti-Truncation Missing
**Evidence (Step 2 — Intel A):**
- "truncated/incomplete" = #1 phrase in m2.7 loss rationales: **3,058 UPDATE**, **1,775 FEATURE**, **619 BUGFIX** mentions
- M2.7 is bimodal: 31% under-edit (tiny patches missing cascade files), 46% over-edit (bloated)
- Avg m2.7 patch = 335 lines vs reference 724 lines — 2.09x ratio means the under-edit tail is severe

The model doesn't enforce its own output completeness. A patch that appears truncated mid-implementation is an automatic loss — the Sonnet-4.6 judge sees "incomplete" and awards the win to king.

No rule in v71 SYSTEM_PROMPT explicitly says: "produce the complete patch, never stop mid-implementation."

**Expected WR impact if fixed: +10–15%** (Step 2's largest single loss signal)

---

### Root Cause 3: Acceptance Criteria Not Explicitly Enumerated
**Evidence (Step 2 — Intel A):**
- "acceptance criteria" = 2nd most common loss phrase: **2,613 UPDATE**, **1,590 FEATURE**, **532 BUGFIX**
- Winners (claude-opus-4.7, 85% WR): explicitly match EACH AC bullet to a code change in their rationale
- M2.7: addresses the headline feature but skips AC bullets (e.g., error handling for edge case)

v71 added the rubric injection (Scope Completeness 30pts, AC 20pts) — correct but insufficient. The model needs a **checklist protocol**: enumerate ACs before finalizing, verify each is addressed.

**Expected WR impact if fixed: +8–12%**

---

### Root Cause 4: UPDATE Tasks — Wiring Protocol Incomplete Without Runtime Tracing
**Evidence (Step 2 — Intel C, D):**
- 396 "end-to-end" + 634 "integration" + 231 "wires" mentions in UPDATE losses
- Claude-opus-4.7 (85% WR) ALWAYS traces: new data/state enters system → flows through state management → surfaces to user → cascade to consumers
- 1,062 wiring examples show consistent pattern: winners wire new features into ALL lifecycle layers (auth gates, store subscriptions, effect dependencies, persistence hooks)
- M2.7 WR on UPDATE = **9%** (vs 11% BUGFIX, 10% FEATURE/API) — UPDATE is tied-worst, not worst

v71 added the UPDATE WIRING RULE to SYSTEM_PROMPT (correct). But without a runtime enforcement step (equivalent to king's coverage_nudge checking "did we touch the state management layer? the UI layer?"), the rule is advisory only.

**Expected WR impact if fixed: +5–8%** (UPDATE is 38% of seed-42 gate tasks)

---

### Root Cause 5: Judge Changed — v71 Gate Partially Invalid
**Evidence (Step 1 — Section 1d):**
- PR#1598 (2026-05-19): Judge changed from `openai/gpt-5.4` → `anthropic/claude-sonnet-4.6`
- Formula changed: `0.5×cursor_sim + 0.5×llm_score` → **`1.0×llm_score`** (cursor_sim = telemetry only)
- v71's 47% gate was run against the OLD judge
- King's SYSTEM_PROMPT still says "similarity to reference patch" — exploitable stale framing
- Our v71 added the correct rubric (Root Cause 40 + Scope 30 + AC 20 + Quality 10) — good

vNext gate will be under a different judge than v71. The true WR delta of our vNext changes vs v71 cannot be compared directly. This is NOT a loss root cause, but it means: **vNext gate results are a fresh baseline, not a comparison to v71.**

**Expected WR impact of realigning SYSTEM_PROMPT framing: +2–4%** (remove cursor_sim framing, emphasize sonnet-4.6 rubric criteria)

---

## King vs Us: Structural Differences

| Capability | King (d24c9d30) | Our v71 | vNext Fix |
|-----------|-----------------|---------|-----------|
| Emergency fallback (budget exhausted) | `_solve_emergency_single_shot` — picks 1 file, forces minimal patch | ❌ Missing — empty patch on timeout | ✅ Port from king exactly |
| Coverage enforcement | `_uncovered_required_paths()` → `coverage_nudge` refinement | ❌ No equivalent | ✅ Add coverage_nudge gate |
| Anti-truncation | Runtime multi-shot + refinement gates prevent partial output | ❌ No runtime enforcement | ✅ Add explicit SYSTEM_PROMPT rule + verify via refinement |
| AC verification | Criteria nudge refinement turn | ❌ Not in our loop | ✅ Add criteria gate to refinement |
| UPDATE wiring | No explicit rule (king uses "smallest correct change" — relies on LANGUAGE-SPECIFIC COMPLETENESS) | ✅ v71 added WIRING RULE | ✅ Keep + add runtime tracing enforcement |
| SYSTEM_PROMPT judge alignment | Stale (still says "similarity to reference") — EXPLOITABLE | ✅ v71 added correct rubric | ✅ Keep + remove cursor_sim framing |
| Completeness asymmetry | LANGUAGE-SPECIFIC COMPLETENESS RULES (Java/C++/TS/Go/Dart) | ❌ No language-specific rules | ✅ Port language-specific completeness section |

---

## The 5 Changes for vNext (ranked by WR impact)

### 1. Port `_solve_emergency_single_shot` from King (CODE CHANGE)
**Evidence:** Step 1: king_agent.py:~3556 — explicit runtime emergency fallback. Every timeout → empty patch → automatic loss. All v62–v71 missing this.
**Implementation:** Copy the emergency single-shot method from king exactly. Wire into the main solve loop: `if remaining_budget < 60s AND no patch yet → _solve_emergency_single_shot()`. Pick 1 high-confidence target file, read 2000-char snippet, produce minimal but non-empty patch.
**Expected impact: +12–18% WR** (highest — removes an entire loss category)

### 2. Add Anti-Truncation Imperative to SYSTEM_PROMPT
**Evidence:** Step 2: "truncated/incomplete" = #1 loss phrase across ALL types (3,058 + 1,775 + 619 mentions). M2.7's 31% under-edit tail is catastrophic for completeness-scored tasks.
**Implementation:** Add to SYSTEM_PROMPT (near the COMPLETENESS ASYMMETRY rule):
```
CRITICAL — NEVER TRUNCATE: Your patch MUST be complete. Never stop mid-implementation, 
never leave a function partial, never indicate "continue from here." If the patch is 
large, produce ALL of it. A truncated patch is an automatic loss regardless of quality.
The judge sees "appears incomplete/truncated" and immediately awards the win to the other patch.
```
**Expected impact: +10–15% WR**

### 3. Add Explicit Acceptance Criteria Checklist Protocol
**Evidence:** Step 2: "acceptance criteria" = 2nd loss phrase (2,613 + 1,590 + 532 mentions). Winners enumerate each AC bullet and verify it has a code change.
**Implementation:** Add to SYSTEM_PROMPT:
```
ACCEPTANCE CRITERIA PROTOCOL: Before producing your patch, extract every AC bullet from 
the issue. After implementing, verify each AC bullet has a corresponding code change.
If any AC bullet is unaddressed — add it before finalizing. The judge scores AC coverage 
at 20 points. Missing AC bullets = guaranteed point deduction.
```
**Expected impact: +8–12% WR**

### 4. Port Language-Specific Completeness Rules from King
**Evidence:** Step 1: king_agent.py:2951 has LANGUAGE-SPECIFIC COMPLETENESS RULES (Java, C/C++, TypeScript/C#, Go/Rust, Dart/Flutter). Step 2: M2.7's bimodal failure (31% under-edit) is language-specific — it misses .h files for C++, implementing classes for TypeScript, all screens for Flutter.
**Implementation:** Port king's language-specific section verbatim. These are the king's primary completeness enforcement mechanism in SYSTEM_PROMPT (since king has no explicit COMPLETENESS ASYMMETRY statement — it uses these concrete rules instead).
**Expected impact: +5–8% WR** (eliminates systematic under-edits on language-specific cascades)

### 5. Realign SYSTEM_PROMPT to Sonnet-4.6 Judge Rubric
**Evidence:** Step 1: PR#1598 removed cursor_sim. King's SYSTEM_PROMPT still says "similarity to reference patch" — stale, exploitable. v71 added the correct rubric (40+30+20+10). Keep v71's rubric. Remove cursor_sim framing. Add explicit "do not optimize for reference similarity."
**Implementation:**
```
Do NOT optimize for similarity to any reference patch. The judge scores only:
- Root Cause Resolution (40pts): Did you fix the OWNER of the behavior?
- Scope Completeness (30pts): Did you touch ALL required files?
- Acceptance Criteria (20pts): Did you satisfy every AC bullet?
- Code Quality (10pts): Is the code idiomatic, tested, safe?
```
**Expected impact: +2–4% WR** (alignment bonus; prevents wrong optimization direction)

---

## What NOT to Change

These patterns caused regressions in v59–v71. They are FORBIDDEN:

❌ **Never-delete rule**: Any rule resembling "Never delete or remove existing functions/components unless the task explicitly requests it." This collapsed REFACTOR from 60% → 0% in v59. REFACTOR tasks REQUIRE deletion.

❌ **Pure minimalism without completeness asymmetry**: "smallest correct change, no more" framing WITHOUT the asymmetry statement. Without asymmetry, the model under-edits on UPDATE/FEATURE tasks.

✅ **REQUIRED — Completeness Asymmetry (must stay):**
> "COMPLETENESS BEATS MINIMALISM. Under-editing (missing a cascade file) is penalized MORE than slight over-editing. When in doubt, include the file."

✅ **REQUIRED — UPDATE WIRING RULE (from v71, must stay):**
The wiring protocol for UPDATE tasks. Do not strip this. The data shows 396 "end-to-end" + 231 "wires" loss mentions — the rule is directionally correct even if insufficient alone.

✅ **REQUIRED — ROOT CAUSE RULE (from king, already in v71):**
> "Patch the owner of the behavior, not a downstream symptom."

---

## Success Metric

**Gate threshold:** ≥70% WR on 100 tasks (seed 42, `--timeout 600`, `--parallel 3`)
**Gate command:**
```bash
python3 validator_harness_v6.py --challenger agent_vNext.py --king king_agent.py --tasks 100 --seed 42 --parallel 3 --timeout 600
```

**Expected vNext WR if all 5 changes applied:** ~65–72% WR (conservative)
- Baseline: 47% (v71, old judge)
- Change 1 (emergency single-shot): +12–18% → ~59–65%
- Change 2 (anti-truncation): +10–15% on remaining losses → ~65–72%
- Changes 3–5: further marginal gains but overlapping with above

**Caveat:** v71 was gated against old gpt-5.4 judge. vNext will gate against claude-sonnet-4.6. The 65–72% estimate assumes new judge behavior is roughly equivalent. Do NOT compare vNext gate result directly to v71's 47% — different judge.

**Priority order for implementation:**
1. `_solve_emergency_single_shot` (code) — must be ported first, highest mechanical impact
2. Anti-truncation + AC checklist (SYSTEM_PROMPT) — single SYSTEM_PROMPT edit session
3. Language-specific completeness rules (SYSTEM_PROMPT) — port from king verbatim
4. Judge rubric realignment (SYSTEM_PROMPT) — minor cleanup

---

*Synthesized from: SOURCE_INTEL_SN66_vNEXT.md (Step 1) + DATA_INTEL_SN66_vNEXT.md (Step 2)*

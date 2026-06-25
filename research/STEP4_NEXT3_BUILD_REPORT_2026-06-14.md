# STEP 4 — Next3 Build Report (SN66 Ninja) — 2026-06-14

**Builder:** SN66 Next3 Build subagent (Opus 4.8)
**Base:** `agent_cl_gpt_Next2.py` (964L) — per task contract (NOT king, NOT Next1)
**Output:** `agent_cl_gpt_Next3.py` (983L, +19L)
**Status:** Built + Step-5 checklist PASS. NOT gated, NOT submitted (James approves first — L-NO-AUTO-SUBMIT-1).

---

## 1. Objective

Next2 final gate: **85% WR (23W/4L/3T)**. All four losses were **BUGFIX**.

| Task type | Next2 result | Next3 target | Action |
|-----------|-------------|--------------|--------|
| BUGFIX | 11W/4L = **73%** | **85%+** | 🎯 fix |
| FEATURE | 5W/0L = 100% | 100% | 🔒 untouched |
| API | 4W/0L = 100% | 100% | 🔒 untouched |
| UPDATE | 1W/0L = 100% | 100% | 🔒 untouched |
| OTHER | 1W/0L = 100% | 100% | 🔒 untouched |

**Design constraint:** every change is BUGFIX-scoped. No working task type's code path was altered.

---

## 2. Root cause (why Next2 still loses 27% of BUGFIX)

Next2's BUGFIX injection (`_STRATEGY_BUGFIX`) was correct-but-terse: "find the line → trace → fix root cause → syntax check → surgical." It named the right discipline but did not give the model an **executable procedure**, so 4/15 BUGFIX tasks still failed via the known failure modes:

1. **Wrong line identified** — no forced reproduce/grep step, so the model guessed the origin.
2. **Symptom patched** — model added a null check at a caller instead of fixing the source.
3. **Churn penalty** — model made the correct fix but also added logging/comments/refactor; the Gemini judge penalizes unrelated changes (`out of scope` loss signal, STEP2 Intel E).
4. **Multi-file miss** — a signature/return-type change fixed one file but left callers broken (`partial implementation`, the #1 BUGFIX loss class).

---

## 3. Changes applied (exactly the 4 specified)

### Change 1 — Strengthened BUGFIX protocol (`_STRATEGY_BUGFIX`)
Replaced the 5-line terse protocol with an explicit STEP 1→4 procedure:
- **STEP 1 — REPRODUCE:** `grep -rn "<error_keyword>" . --include=...` to locate the EXACT origin file/line before touching code (kills "wrong line" failures).
- **STEP 2 — TRACE TO ROOT CAUSE:** read the full enclosing function, enumerate common root causes, **"DO NOT fix callers — fix the origin"** (kills symptom-patch failures).
- **STEP 3 — ONE SURGICAL EDIT:** smallest change; 1-line bug → 1-line fix; explicit ban on logging/comments/error-handling/refactor unless the issue requires it (kills churn).
- **STEP 4 — VERIFY:** re-read changed lines; `python -c "import ast; ast.parse(...)"` on edited Python; undo+retry from Step 1 if the fix doesn't match the described behavior (kills partial/early-stop fixes).

### Change 2 — Anti-churn guard in the base SYSTEM_PROMPT
Added a `## BUGFIX MINIMAL-CHANGE RULE` block inside the existing **SCOPE DISCIPLINE** section (kept paired with the minimalism counterbalance, not before COMPLETENESS BEATS MINIMALISM):
> "BUGFIX: change the minimum number of lines. The judge penalizes unrelated changes. A 1-line fix that solves the root cause beats a 10-line refactor every time. This rule applies ONLY to bug fixes — it never overrides COMPLETENESS BEATS MINIMALISM for FEATURE/UPDATE tasks, where every requirement must be met."

The trailing clause is a deliberate safety scope-fence so the anti-churn rule cannot bleed into FEATURE/UPDATE (those are at 100% — must not regress toward under-editing, FORBIDDEN Pattern 2).

### Change 3 — Multi-file BUGFIX awareness
Inserted into STEP 2 of the BUGFIX injection:
> "Multi-file check: if the bug involves a function called from multiple places, check if the fix needs to propagate (e.g. changed return type -> update callers). Run: `grep -rn '<function_name>' . | head -10`"

Directly targets the `partial implementation` / `updates four required` loss class (STEP2 Intel A/B) for BUGFIX.

### Change 4 — Updated docstring
Rewrote the module docstring to Next3, listing the three BUGFIX improvements and explicitly noting all Next2 strengths preserved. No king SHA / "flattened copy" language (CI lesson).

---

## 4. What was NOT touched (preservation proof)

- `_detect_task_type`, `_STRATEGY_UPDATE`, `_STRATEGY_FEATURE`, `_STRATEGY_OTHER`, `_ANALYSIS_DIRECTIVE`, `build_task_type_preamble` — unchanged → UPDATE/FEATURE/API/OTHER protocols identical to Next2.
- `ChatModel` empty-reply rejection (`ae2158103232`), list-shaped content parsing — unchanged.
- `_NATIVE_TOOL_CALL_RE` + bash-block dual-format parsing — unchanged.
- `render_observation` graduated urgency + solve-time awareness — unchanged.
- `_sanitize_patch` — **log-only, no line drop** (CI lesson) — unchanged.
- `_EDGECASE_GUARDRAIL` — unchanged; contains NO `grader` / `reward model` (CI lesson).
- `solve()` signature — unchanged.
- No third-party deps, no sampling params, no hardcoded models/keys.

**Net delta vs Next2: +19 lines, entirely BUGFIX-scoped.**

---

## 5. Step-5 Checklist Results (all PASS)

```
✅ syntax              python3 -m py_compile agent_cl_gpt_Next3.py
✅ import OK           from agent_n3 import solve
   def solve count = 1
✅ completeness        COMPLETENESS BEATS MINIMALISM present
✅ no sampling         no temperature/top_p/top_k (non-comment)
✅ no CI risk          no grader / reward model
   wc -l = 983
```

Extra CI-lesson checks:
```
✅ no king SHA / "flattened" in docstring
✅ _sanitize_patch log-only (Log-only comment + print warning + return diff_output, no line drop)
✅ guardrail tuple clean (no grader / reward model)
✅ new BUGFIX protocol present (STEP 1 REPRODUCE / Multi-file check / ONE SURGICAL EDIT)
✅ anti-churn rule present (BUGFIX MINIMAL-CHANGE RULE)
```

---

## 6. Expected impact & risk

- **BUGFIX 73% → ~85%+ (target):** the four BUGFIX loss modes each get a dedicated, executable mitigation (reproduce → trace-origin → surgical+anti-churn → verify/undo).
- **FEATURE/API/UPDATE/OTHER:** zero code-path change → expected to hold at 100%. The anti-churn rule is explicitly fenced to BUGFIX so it cannot induce under-editing on completeness-driven types.
- **CI risk:** minimal — small delta on a king-derived lineage, no forbidden phrases, prompt-only + injection-only changes. CI risk profile unchanged from Next2.
- **Residual risk:** the strengthened protocol adds ~1–2 investigation steps on BUGFIX; well within the 50-step / wall-clock budget. Solve-time weight is only 5% and the protocol still pushes toward the smallest fix.

---

## 7. Next steps (NOT executed here)

1. James reviews this report + the four diffs.
2. On approval: sync current king, gate with `--judge-model google/gemini-3.1-flash-lite` (judge changed — all Sonnet-era gate data invalid per STEP3), `--timeout 600`, report WR by task type only after ≥40/50 tasks (L-SN66-GATE-REGRESSION-1).
3. Confirm BUGFIX ≥85% AND no regression on FEATURE/API/UPDATE/OTHER before any submission.
4. NEVER auto-submit — explicit James approval required (L-NO-AUTO-SUBMIT-1).

---

*Built by Opus 4.8 subagent | base Next2 | 2026-06-14 | not gated, not submitted*

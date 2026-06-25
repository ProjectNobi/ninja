# SN66 Next17 Build Report — 2026-06-16

**Builder:** SN66 Next17 Builder (subagent)
**Output agent:** `/root/sn66-ninja/agent_cl_gpt_Next17.py`
**Base:** `agent_cl_gpt_Next16.py` (1409L) — itself a flat re-base on king `16e2f934`
**King reference:** `/root/sn66-ninja/king_agent.py` (1560L inlined)
**Line count:** 1472L (Next16 was 1409L; +63L = the three changes + their comments + an updated header docstring)

---

## Why Next17 exists — the Next16 gate failure

Next16 gate: **❌ FAIL — W3 / L5 / T1 = 37.5% WR** (need 57%+), Gemini Flash Lite judge.

| Task | Type | Lang | Result | Score | Root cause |
|------|------|------|--------|-------|------------|
| 1 | BUGFIX | C/C++ | ✅ WIN | 0.950 | — |
| 2 | BUGFIX | Python | ❌ LOSS | 0.750 | King patch more complete |
| 3 | BUGFIX | TypeScript | ❌ LOSS | 0.000 | **TIMEOUT 300s** |
| 4 | API/ROUTE | Python | ✅ WIN | 0.920 | — |
| 5 | API/ROUTE | PHP | ❌ LOSS | 0.750 | King patch more complete |
| 6 | BUGFIX | Go | ✅ WIN | 0.350 | — |
| 7 | API/ROUTE | JavaScript | ❌ LOSS | 0.200 | Near-collapse — partial impl |
| 8 | BUGFIX | TypeScript | 🤝 TIE | 0.000 | **Double timeout** |
| 9 | FEATURE | TypeScript | ❌ LOSS | 0.000 | **TIMEOUT + collapse** |

**Diagnosis (two distinct loss buckets):**

1. **Timeout bucket (tasks 3, 8, 9 — all TypeScript, all 0.000).** Large multi-file repos. Our agent burned its step budget on exploration (reading files, grepping, understanding) and was still navigating at step 15 while the king's minimal loop had already fixed and submitted. The king's only "wrap up" nudge fires at `remaining_steps <= 3` — far too late on a timeout task.
2. **Moderate-loss bucket (tasks 2, 5, 7 — score 0.20–0.75).** King's patch was simply more *complete* than ours. Root cause traced to `extract_criteria`: when an issue's text carries no bullet / numbered / imperative requirements, it returns an empty list → the acceptance checklist is blank → the model gets **zero completeness nudge**.

The robust fence parser (Next16's headline addition) did **not** address either bucket — confirmed a wrong hypothesis for the timeouts. It is *kept* (it fixes a real, separate empty-diff failure mode), but it was orthogonal to this gate's losses.

---

## The three (and only three) changes vs Next16

### CHANGE 1 — Earlier + escalating step pressure (HIGHEST PRIORITY, timeout fix)
**File location:** inlined `render_observation()`

Before (Next16): a single nudge at `remaining_steps <= 3`.
After (Next17): two-tier escalation —
- `remaining_steps <= 6` → *"Stop exploring — apply your fix now, wire every new symbol into its call sites, then submit."*
- `remaining_steps <= 3` → hard *"FINAL — Submit NOW with `echo …`, do not read more files."*

This pushes the model off exploration and into action several steps sooner — exactly the lever the large-TypeScript timeouts need. Verified tier behavior:

```
remaining=10 -> none(>6)     remaining= 5 -> STOP(<=6)
remaining= 7 -> none(>6)     remaining= 4 -> STOP(<=6)
remaining= 6 -> STOP(<=6)    remaining= 3 -> FINAL(<=3)
                             remaining= 1 -> FINAL(<=3)
```

> Note: the `<=3` note text contains the COMPLETION_SENTINEL `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`, whose name embeds the substring "FINAL" — a naive `'FINAL' in note` check gives a false positive at the STOP tier. The real escalation (verified by full-text inspection) is correct: `>6` quiet, `4–6` STOP, `1–3` FINAL.

### CHANGE 2 — Action-first SYSTEM_PROMPT rider line
**File location:** `SYSTEM_PROMPT`

Appended exactly one neutral action-bias line to the existing rider:
> *"On large or multi-file tasks, make your first edit within 4 steps — do not spend more than 3 steps reading before writing a fix."*

This is a single line, **not** a new SYSTEM_PROMPT section (the Next15 over-prompting regression lesson is respected). SYSTEM_PROMPT is now 18 non-blank lines (king's ~15 + 3-line rider + this 1 line ≈ within the "21 lines + small rider" budget).

### CHANGE 3 — Fallback minimum checklist (moderate-loss completeness fix)
**File location:** `extract_criteria()`, immediately before `return out[:15]`

When fewer than 2 real criteria are extracted, backfill two generic completeness hints:
- "Ensure every file mentioned in the task is edited or created"
- "Wire all new functions/classes/routes into their call sites — no dead code"

So **every** task now carries a non-empty acceptance checklist. Verified:
- Plain issue (no bullets) → 2 criteria (the fallbacks fire) ✅
- Bulleted issue → 4 criteria, fallback does **not** fire ✅

---

## What was deliberately NOT changed (per task constraints)
- ❌ No new SYSTEM_PROMPT sections (Next15 lesson) — rider stays minimal.
- ❌ No GPS ensemble / multi-shot.
- ❌ `max_steps` unchanged (18 is fine — the fix is *how* steps are used, not *how many*).
- ❌ `_sanitize_patch` kept (8 references intact).
- ❌ King's core loop structure untouched.
- ✅ Robust fence parser from Next16 kept verbatim (`_parse_single_command` + fallbacks).
- ✅ Criteria injection + guard heuristics kept.

---

## Mandatory checks — ALL PASSED

| Check | Result |
|-------|--------|
| `python3 -m py_compile agent_cl_gpt_Next17.py` | ✅ COMPILE_OK |
| `python3 -c "from agent_cl_gpt_Next17 import solve; print('OK')"` | ✅ IMPORT_OK |
| grep `remaining_steps <= 6` | ✅ 2 hits |
| grep `FINAL` | ✅ 3 hits |
| grep `4 steps` | ✅ 2 hits |
| grep `_sanitize_patch` | ✅ 8 hits |
| grep `extract_criteria` | ✅ 5 hits |
| grep `patch_acceptable` | ✅ 4 hits |

Functional sanity tests (beyond grep) also passed:
- `render_observation` escalation tiers fire at the correct thresholds.
- Action-first rider line present in `SYSTEM_PROMPT`.
- `extract_criteria` fallback fires only when <2 real criteria found; bulleted issues unaffected.

---

## Confidence assessment

**Moderate-to-good.** Rationale:

- **Change 1 is well-targeted at the dominant loss bucket.** All three 0.000 losses were TypeScript timeouts, and the king (whose minimal loop we are now mimicking via earlier pressure) completed those same tasks. Pushing pressure from step ≤3 to step ≤6 is a direct, low-risk countermeasure. *Risk:* prompt-level nudges only *bias* the model — they do not *force* it to stop reading. A genuinely large repo may still time out if 6 steps of remaining budget is itself insufficient to write a correct multi-file fix. This is the single biggest residual risk.
- **Change 3 is low-risk and additive** — it only adds a checklist where one was previously blank, and provably does not touch issues that already have requirements. Whether two generic hints close the 0.20–0.75 completeness gap on tasks 2/5/7 is unproven (the king's TASK_TEMPLATE completeness language was already present; this just guarantees a checklist exists).
- **Change 2 reinforces Change 1** at the system level with one neutral line — cheap, consistent with the kept-lean philosophy, minimal regression risk.

**Caveats for the gate:**
- The fixes are *prompt-level behavioral nudges*, not structural guarantees. If the timeout tasks need genuinely more wall-clock than the loop allows (not just earlier action), Next17 will still time out and the next step is to investigate `command_timeout` / observation truncation / wall-clock budget rather than more prompting.
- Judge variance (Gemini Flash Lite) on a 10-task gate is high; a single timeout flipping to a completed-but-mediocre patch can swing WR by 10%+. Recommend the gate be read for the *timeout count* (did tasks 3/8/9 stop hitting 0.000?) as the primary signal, not just the headline WR.

**Recommendation:** Next17 is ready for gate testing (not run here, per instructions). Primary success signal to watch: **do the TypeScript tasks stop scoring 0.000?** Secondary: do tasks 2/5/7 move above 0.75?

---

## Files
- Agent: `/root/sn66-ninja/agent_cl_gpt_Next17.py` (1472L)
- This report: `/root/sn66-ninja/research/STEP4_NEXT17_BUILD_2026-06-16.md`
- Base: `/root/sn66-ninja/agent_cl_gpt_Next16.py` (1409L)
- King: `/root/sn66-ninja/king_agent.py` (1560L, `16e2f934`)

**No gate tests run. Nothing submitted.** (per task constraints)

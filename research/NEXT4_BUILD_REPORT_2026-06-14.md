# Next4 Build Report — SN66 Ninja Miner
*Built: 2026-06-14 | Builder: Opus 4.8 subagent | Target: beat new king `01c675065c1c` (775L)*

---

## 1. Objective

Build `agent_cl_gpt_Next4.py` to beat the **new burn king** (`unarbos/ninja`,
sha `01c675065c1ca3216d4b7b6cecf03c7f37405e46`, 775L flattened). Next2-v3 lost
the gate at **43% WR** (30 tasks, seed 42) — every task type was losing or tying:

| Type | Next2-v3 result | WR |
|------|-----------------|----|
| BUGFIX | 5W/7L | 41% ← worst |
| FEATURE | 2W/2L | 50% |
| API | 2W/2L | 50% |
| UPDATE | 1W/1L | 50% |
| OTHER | 0W/1L | 0% |

---

## 2. Root-cause analysis

### Files read in full (mandatory)
- `king_agent.py` (775L) — new king, every line read
- `agent_cl_gpt_Next2v3.py` (945L) — build base
- `research/FINAL_SN66_PIPELINE.md` — pipeline rules
- `research/STEP2_DATA_INTEL_2026-06-14.md` — judge intel

### Confirmed: the verify-repair pass is NOT the gap
Both `king_agent.py` and `Next2v3.py` contain the **identical** verify-repair
machinery: `_changed_py_files` → `_py_syntax_errors` → `_repair_reason` →
`_build_repair_task`, wired into `solve()` with `VERIFY_REPAIR_MIN_BUDGET_SECONDS`
and `VERIFY_REPAIR_MAX_STEPS`. Next2-v3 already inherits this. So the loss is not
a missing repair pass.

### The real gap: SYSTEM_PROMPT additions FIGHT the king's TASK_TEMPLATE
The new king's TASK_TEMPLATE is well-calibrated for the judge. It already says:
- "make the fix correct and **COMPLETE**"
- "Keep the change **tightly scoped** — no unrelated edits, no churn, no empty diffs"
- "Demonstrate it is correct with a focused test, a reproduction, or assertions"
- A full `## Workflow` (6 steps) + `## Hard rules`

Next2-v3 then bolted TWO extra blocks onto the **SYSTEM_PROMPT**:
- `## COMPLETENESS BEATS MINIMALISM` ("under-editing costs MORE than over-editing")
- `## ACCEPTANCE CRITERIA FIRST`

These push the model toward **over-editing / broader patches**, directly
contradicting the king template's "tightly scoped, no churn" instruction the
same model reads in the user turn. The model receives conflicting pressure →
inconsistent patches → loses on both fronts (churn-penalized AND incomplete).
This is the dominant root cause of the across-the-board 43% loss.

### Why this is consistent with the data intel
`STEP2_DATA_INTEL_2026-06-14.md` confirms the live Gemini judge's #2 loss cause
is **scope creep** (649 lessons; "out of scope / unnecessary changes" = explicit
penalty) while #1 is **partial implementation** (967 lessons). The king
TASK_TEMPLATE already balances both. Adding a one-sided "completeness beats
minimalism" SYSTEM_PROMPT block over-corrects toward scope creep.

---

## 3. Changes applied (Next2-v3 → Next4)

Base: `cp agent_cl_gpt_Next2v3.py agent_cl_gpt_Next4.py` (verify-repair pass +
task-type detection inherited intact).

### Change 1 — Remove conflicting SYSTEM_PROMPT additions
Removed `## COMPLETENESS BEATS MINIMALISM` and `## ACCEPTANCE CRITERIA FIRST`
from the SYSTEM_PROMPT. **Kept only** the `## BUGFIX MINIMAL-CHANGE RULE` — it is
targeted, reinforces the king template's "tightly scoped" direction, and does not
conflict.

### Change 2 — Correctness-demonstration nudge in task-type protocols
The king template rewards "demonstrate it is correct." Added matching nudges:
- **UPDATE** step 6: "After wiring: add one assertion or log statement that proves the new code runs."
- **BUGFIX** step 6: "After fixing: write a 1-line verification (print/assert) that shows the bug is gone. Then remove it before submitting."
- **FEATURE**: "After implementing: demonstrate end-to-end with a minimal test or reproduction step."

### Change 3 — Extended TASK_TEMPLATE `## Workflow`
Added a `## Prioritised steps` block (5 steps: read fully → root cause → smallest
change satisfying all criteria → re-read for unrelated edits → ast.parse check)
right after the existing Workflow's `echo {sentinel}` step.

### Change 4 — Improved task-type detection
- Added a dedicated **REFACTOR** type (`refactor`, `restructure`, `reorganize`,
  `clean up`, `cleanup`, `tidy up`, `extract method`, `deduplicate`).
- Tightened `_UPDATE_KEYWORDS`: removed generic `update`, `connect`,
  `modify existing`, and moved `refactor` out to REFACTOR — these were stealing
  BUGFIX/OTHER tasks (the FINAL_SN66 doc + STEP2 intel show generic "update"
  over-fires).
- Detection priority: REFACTOR (when no bug signal) → BUGFIX → UPDATE → FEATURE
  → OTHER. A refactor task that ALSO names a bug routes to BUGFIX (fix is the
  dominant requirement).
- New REFACTOR strategy block: "Make structural changes only — do not change
  behavior. Tests must still pass."

### Change 5 — Clean docstring
Rewrote module docstring to describe Next4 (no "flattened king" language).

---

## 4. Verification (Step 5 checklist — ALL PASS)

```
✅ syntax            (python3 -m py_compile)
✅ import OK         (from agent_n4 import solve)
✅ repair pass       (_repair_reason + _build_repair_task present)
✅ task detection    (_detect_task_type present)
✅ no sampling       (no temperature/top_p/top_k)
✅ clean             (no grader / reward model)
   976 lines
```

Additional checks:
- `✅ solve() signature IDENTICAL to king` (diff clean)
- `✅ COMPLETENESS BEATS MINIMALISM / ACCEPTANCE CRITERIA FIRST removed`
- `✅ BUGFIX MINIMAL-CHANGE RULE kept`
- `✅ REFACTOR fully wired` (keywords + detection + strategy + map entry)
- `_sanitize_patch`: not present in this base (king/Next2-v3 never had it) — rule trivially satisfied, nothing to violate.
- No hardcoded keys/models/endpoints/wallet refs.

### Task-type detection smoke test — 8/8 correct
```
✅ BUGFIX   :: Fix the bug where login crashes on null email
✅ REFACTOR :: Refactor the payment module to extract a helper class
✅ REFACTOR :: Restructure and clean up the utils directory
✅ UPDATE   :: Upgrade the finch package and migrate the API calls
✅ FEATURE  :: Add a new dark-mode toggle feature to settings
✅ FEATURE  :: Implement support for CSV export
✅ BUGFIX   :: Refactor the parser but it currently crashes on empty input  (bug wins over refactor)
✅ OTHER    :: Improve the dashboard layout
```

---

## 5. Open risk / tension flagged for review

⚠️ **Pipeline-doc tension (must surface to James/audit before submit).**
`FINAL_SN66_PIPELINE.md` lists `COMPLETENESS BEATS MINIMALISM` + the
under-editing asymmetry statement as **REQUIRED patterns** and warns against
"pure minimalism without asymmetry" (L-SN66-MINIMALISM-FRAMING-1,
L-SN66-NEVER-DELETE-RULE-1). Next4 **removes those exact blocks from the
SYSTEM_PROMPT**.

Rationale this is acceptable (per build brief):
1. The completeness signal is **NOT** lost — it lives in the king TASK_TEMPLATE,
   which Next4 keeps intact ("make the fix correct and COMPLETE", "completeness
   is rewarded"). So Next4 is **not** "pure minimalism without asymmetry" — the
   asymmetry is preserved at the user-turn level.
2. The required-pattern guidance predates this **new burn king**, whose own
   TASK_TEMPLATE already embeds the completeness+scope balance. Stacking a
   second one-sided SYSTEM_PROMPT block on top is what created the conflict.
3. No "never delete" pattern is present anywhere (REFACTOR strategy explicitly
   permits deletion) — L-SN66-NEVER-DELETE-RULE-1 is honored.

**This is a deliberate, brief-mandated deviation. The gate test will validate it.**
If the gate regresses below Next2-v3's 43%, revert Change 1 and re-test with the
asymmetry block kept only as a balanced statement.

---

## 6. Next steps (NOT auto-executed — James approves)
1. King sync check: `bash scripts/sync_king.sh && wc -l king_agent.py`.
2. Gate test in tmux: `validator_harness_v6.py --challenger agent_cl_gpt_Next4.py --king king_agent.py --tasks 50 --seed 42 --parallel 3 --timeout 600`.
3. Threshold ≥60% decisive WR; report breakdown by task type.
4. **Do NOT submit without James's explicit approval** (L-NO-AUTO-SUBMIT-1).

---

## 7. Deliverables
- `agent_cl_gpt_Next4.py` (976L) — built, syntax-clean, import-clean, all gates pass.
- This report.

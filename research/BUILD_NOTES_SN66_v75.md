# BUILD_NOTES_SN66_v75.md

## Summary
v75 = king clone with ONE targeted sentence added to the INSPECTION STRATEGY section.

---

## Exact Diff

```diff
2884c2884
< Inspect only what you need to locate the owner of the bug and patch safely. Order: preloaded snippets first, then one or two focused searches (`rg`, fall back to `grep -R`), then the exact target region (`sed -n '120,220p'`), then nearby tests, then call sites only if a signature/public API may change.
---
> Inspect only what you need to locate the owner of the bug and patch safely. Order: preloaded snippets first, then one or two focused searches (`rg`, fall back to `grep -R`), then the exact target region (`sed -n '120,220p'`), then nearby tests, then call sites only if a signature/public API may change. If your first edit command has not appeared by your 3rd response, you are over-inspecting — commit to your best diagnosis and start editing now.
```

**Location:** Line 2884 — INSPECTION STRATEGY section  
**Change type:** Append one sentence to existing inspection order instruction

---

## Why This Change

From STEP1 source intel: king wins on quick targeted edits vs agents spending extra steps on inspection. The STEP1 analysis flagged that agents lose rounds by over-inspecting before committing to an edit. The king's INSPECTION STRATEGY already says "preloaded snippets first, then ONE or TWO focused searches" — but this doesn't explicitly time-box the inspection phase.

The added sentence provides a concrete 3rd-response deadline: if no edit has appeared, the agent is over-inspecting and must commit now. This targets the specific failure mode (spending the step budget on inspection rather than producing patches) across ALL task types (BUGFIX, UPDATE, FEATURE, API).

**Debate approval:** Inspection-to-edit ratio reinforcement was the single approved change. All other proposed changes were ruled out.

---

## Why All Other Changes Were Excluded

| Proposed Change | Verdict | Reason |
|---|---|---|
| AC checklist ("All AC points covered") | ❌ EXCLUDED | Redundant with existing `_extract_acceptance_criteria()` runtime injection already in king |
| UPDATE/FEATURE wiring rule block (5+ lines) | ❌ EXCLUDED | Nearly identical to v73's removed rule; king succeeds without it |
| Replace/modify scoring sentence | ❌ FORBIDDEN | Confirmed load-bearing — never touch |
| Verbose rule blocks | ❌ EXCLUDED | Cognitive overhead hurts performance |
| Task-type classification logic | ❌ EXCLUDED | Debate ruled out entirely |

---

## Expected Impact

- **Realistic WR estimate:** +0–3% over king clone baseline
- **Rationale:** Single sentence, targets one specific failure mode. Inspection speed affects patch quality within budget but the king already handles this reasonably. Gate data is the honest truth.
- **No regression risk:** The sentence reinforces existing direction, doesn't contradict any other rule. All task types benefit equally from faster first edit.

---

## Audit Checklist

- [x] Scoring sentence preserved verbatim: `"smallest correct change a senior maintainer would accept"` ✅ (line 2831)
- [x] No new rule blocks added (>5 lines together) ✅
- [x] No task-type classification logic ✅
- [x] No AC checklist addition ✅
- [x] No wiring rule addition ✅
- [x] diff shows exactly 1 logical change ✅ (line 2884 only)
- [x] `python3 -m py_compile agent_cl_gpt_v75.py` passes ✅
- [x] Line count: 4595 (unchanged — sentence appended to same line) ✅

---

## Gate Command

```bash
cd /root/sn66-ninja
tmux new-session -d -s v75gate
tmux send-keys -t v75gate "python3 -u validator_harness_v6.py --challenger agent_cl_gpt_v75.py --king king_agent.py --tasks 100 --seed 42 --parallel 3 --timeout 600 2>&1 | tee /tmp/v75_gate100.log" Enter
```

Monitor:
```bash
tail -f /tmp/v75_gate100.log
```

**Threshold:** ≥70% decisive WR on 100 tasks (James directive 2026-05-17)

After gate completes, kill session:
```bash
tmux kill-session -t v75gate
```

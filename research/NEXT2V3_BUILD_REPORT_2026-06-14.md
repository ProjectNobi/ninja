# SN66 Next2-v3 — Build Report
*Built by: Opus 4.8 subagent | 2026-06-14 ~18:40 UTC*

## Objective
Build `agent_cl_gpt_Next2v3.py` = **new king (776L, SHA `01c675065c1c`) as base** + Next2's **task-type detection layer** + minimal SYSTEM_PROMPT strengthening. Root cause being fixed: Next2 kept failing CI at score 58 because the judge saw our agent as **missing the new king's verify-repair pass** (regression vs new king). Next2-v3 keeps that pass intact while layering on the task-type detection that pushed gate WR 54%→85%.

## Base
- `cp king_agent.py agent_cl_gpt_Next2v3.py` (775L king → 945L final)
- King SHA: `01c675065c1ca3216d4b7b6cecf03c7f37405e46`
- **Verify-repair pass kept 100% intact:** `_changed_py_files`, `_py_syntax_errors`, `_repair_reason`, `_build_repair_task`, and the bounded second-solve block inside `solve()` (`VERIFY_REPAIR_MIN_BUDGET_SECONDS=45`, `VERIFY_REPAIR_MAX_STEPS=14`, "repair pass adopted" only when strictly better). Untouched.

## Additions over king (3 surgical changes)

### 1. Task-type detection (ported verbatim from Next2)
Inserted into the prompts section before `build_task_prompt`:
- `_UPDATE_KEYWORDS`, `_BUGFIX_KEYWORDS`, `_FEATURE_KEYWORDS` tuples
- `_detect_task_type(task_text)` — priority: BUGFIX → UPDATE → FEATURE → OTHER
- `_STRATEGY_UPDATE / _STRATEGY_BUGFIX / _STRATEGY_FEATURE / _STRATEGY_OTHER` blocks
- `_ANALYSIS_DIRECTIVE` (plan files + type + criteria before first command)
- `build_task_type_preamble(task_type)`

### 2. Injection wired into king's `run_agent_loop`
Replaced the king's first user-message construction:
```python
user_content = task if "<task>" in task else build_task_prompt(task_text=task)
task_type = _detect_task_type(user_content)
user_content = user_content + build_task_type_preamble(task_type)
```
plus `log_lines.append(f"[init] detected task_type={task_type}")`.
**Applies to BOTH the initial pass and the repair pass** (repair re-enters `run_agent_loop`), so the repair turn also gets the right protocol — a free improvement.

### 3. SYSTEM_PROMPT strengthened (king's prompt + 3 blocks appended)
Added AFTER the king's existing SYSTEM_PROMPT body:
- `## COMPLETENESS BEATS MINIMALISM` (under-editing costs more)
- `## ACCEPTANCE CRITERIA FIRST`
- `## BUGFIX MINIMAL-CHANGE RULE` (1-line root-cause fix beats 10-line refactor; no gratuitous logging/comments/error handling)

### 4. Docstring updated
Replaced "Flattened king — SHA ..." with the Next2-v3 docstring (no king SHA header, no "flattened" framing). Describes base = new king, additions = task-type detection + SYSTEM_PROMPT rules.

## Design decisions / deviations from the brief
- **No `_sanitize_patch` added.** The brief said "keep king's `_sanitize_patch` if it has one, or add a log-only version." The **new king has neither a `_sanitize_patch` nor a native tool-call regex** (verified: `grep -c _sanitize_patch king_agent.py` = 0). Per `L-SN66-KING-BASE-MANDATORY-1` + `L-SN66-CI-VBASE-MATTERS-1` (any divergence from king lowers CI), I kept `collect_repo_patch` **byte-identical to king** rather than introducing a Next2-style sanitizer. King-base fidelity is the priority; adding the sanitizer would be a divergence that risks the exact CI regression we are trying to escape. Recommend keeping it out unless a future CI failure points to injection content.
- **"native tool-call regex"** referenced in the brief is a Next2 feature (`_NATIVE_TOOL_CALL_RE`), not present in the new king. Not ported, for the same king-fidelity reason. King uses `_ACTION_BLOCK_RE` only — kept as-is.

## Build-rule compliance
| Rule | Status |
|------|--------|
| Base = new king (776L), not Next1/Next2 | ✅ |
| Verify-repair pass intact (not removed/modified) | ✅ |
| No `grader` / `reward model` in guardrails | ✅ (no guardrail list added) |
| No sampling params (temperature/top_p/top_k/seed) | ✅ |
| No hardcoded API keys/model names/provider URLs | ✅ (only king's generic `Bearer {self.auth_token}`) |
| `solve()` signature unchanged | ✅ |
| stdlib only | ✅ |
| No forbidden "never delete" pattern | ✅ |
| COMPLETENESS BEATS MINIMALISM present | ✅ |

## Step 5 checklist — ALL PASS
```
✅ syntax            (py_compile)
✅ import OK         (from agent_n2v3 import solve)
   def solve count  = 1
   _detect/_STRATEGY = 12 matches
✅ completeness      (COMPLETENESS BEATS MINIMALISM present)
✅ repair pass present (_repair_reason + _build_repair_task)
✅ no sampling
✅ clean             (no grader/reward model)
   wc -l            = 945
```
Runtime smoke test of `_detect_task_type`: UPDATE→UPDATE, BUGFIX→BUGFIX, FEATURE→FEATURE, OTHER→OTHER. ✅

## Files
- Agent: `/root/sn66-ninja/agent_cl_gpt_Next2v3.py` (945L)
- Report: `/root/sn66-ninja/research/NEXT2V3_BUILD_REPORT_2026-06-14.md`

## Status
**NOT gated, NOT submitted.** Per `L-NO-AUTO-SUBMIT-1` — James approves before any gate test or submission.

## Recommended next step
Gate test in tmux vs the new king (king is multishot → `--timeout 600`):
```bash
cd /root/sn66-ninja
tmux new-session -d -s sn66_n2v3_gate
tmux send-keys -t sn66_n2v3_gate \
  "python3 -u validator_harness_v6.py --challenger agent_cl_gpt_Next2v3.py \
   --king king_agent.py --tasks 50 --seed 42 --parallel 3 --timeout 600 \
   > /tmp/n2v3_gate_50.log 2>&1" Enter
```
Threshold: ≥60% decisive WR (50 tasks, seed 42).

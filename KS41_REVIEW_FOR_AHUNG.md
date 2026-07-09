# KS41 — Review Brief for A Hung
**Author: Dragon Lord 🐉 (Fable-5) | 2026-07-09**
**Branch: `kingslayer/ks40` | Commit: `471d4cb` | File: `agent_cl_gpt_KingSlayer41.py` (2296 lines)**
**CI: PASS** (py_compile OK, `from agent import solve` OK as standalone file, no forbidden sampling params, solve() contract intact)

---

## What KS41 is

**KS41 = KS39 (the challenger that BEAT this king family, mean 0.729) + exactly three changes.**
It is NOT based on KS40 (which regressed to 0.699 and lost duel 251186). Everything outside the
three changes below is byte-identical to `agent_cl_gpt_KingSlayer39_submitted.py`.

## The three changes (all line numbers in agent_cl_gpt_KingSlayer41.py)

### 1. King-faithful best-of-two reroll (PRIMARY)
- **New block:** lines ~1817–2135 (`# KS41: king-faithful best-of-two reroll`).
- **Wiring:** in `solve()`, `outcome = _run_loop(config, task)` is replaced by
  `outcome = _run_best_of_two_ks41(config, task, issue)` with a bare-`_run_loop` fallback
  on any orchestrator exception (lines ~2168–2174).
- Ported from `agent/reroll.py` function-by-function, adapted only to KS39's internals
  (`_run_loop` instead of `run_agent_loop`, `_collect_repo_patch` instead of
  `collect_repo_patch`, `RunOutcome`/`dataclasses.replace`):
  - `_run_best_of_two_ks41` ← `run_best_of_two` (same control flow, same guard order,
    same fall-open-to-attempt-#1 on every failure path)
  - `_is_weak_ks41` ← `_is_weak` — **the king's exact four conditions, nothing more**
  - `_measure_ks41` ← `_measure` (verbatim, incl. substantive-line/trivial logic)
  - `_key_ks41` ← `_key` (verbatim 5-tuple, size-excluded, strictly-greater adoption)
  - `_reset_verify_ks41` ← `_reset_verify` — **includes the `_collect_repo_patch(repo).strip()==""`
    verification that KS40's `_git_reset_verify_ks40` dropped** (dirty-copy inheritance bug)
  - `_materialize_ks41`, `_git_apply_ks41` (no `--index`, `--3way` fallback), `_git_out_ks41`,
    `_git_run_ks41`, `_touched_paths_ks41`, `_all_py_parse_ks41`, `_touches_named_ks41`,
    `_named_reqs_ks41`, `_named_tokens_ks41`, `_outcome_on_disk_ks41`, `_floor_outcome_ks41`
  - Constants: `ATTEMPT2_MIN_REMAINING=160`, `ATTEMPT2_MARGIN=100`, `MIN_ATTEMPT2_WALL=60`,
    `GIT_TIMEOUT=30` — all identical to king.
- KS39's proven repair/rescue pipeline in `solve()` still runs AFTER the reroll, unchanged
  (its own budget guards already handle a reroll-consumed wall).

### 2. Wall budget matches king (line ~253)
- `_FALLBACK_WALL_CLOCK 270.0 → 280.0`, `_WALL_CLOCK_MARGIN 30.0 → 20.0`.
- The 270/30 rule was our own gate.sh convention, not a validator constraint; the king runs
  280/20 inside the same 300s SIGKILL and wins. Removes a 10s/round handicap.
- ⚠️ **Note for you:** `scripts/gate.sh` may still assert 270/30 — if it flags KS41, the
  guardrail needs updating, not the agent.

### 3. `_KS41_MATERIALIZE_MIN = 30.0` (king uses 15.0)
- Widens the do-not-swap window before the SIGKILL so the `git reset --hard` → `git apply`
  materialize sequence can never straddle the kill (suspected cause of KS40's R16 = 0.000).
- Only deliberate deviation from the king's constants. Trade-off: in rare 15–30s-left cases
  we keep attempt #1 instead of swapping — strictly safer.

## KS40 false positives fixed (by omission — none of this code exists in KS41)
- `_is_hard_task_ks40` / `_HARD_TASK_NOTE` scope injection: removed (noise on well-specified tasks).
- `_is_weak_patch_ks40`: replaced by the king's exact `_is_weak` on `_measure` output. Note my
  audit finding: post-FIX-4, KS40's conditions 3/4 were closer to king's than the post-mortem
  claims — the bigger deltas were the missing reset-verify patch check, the 270s budget, and
  extra KS40 surface (hard-task note) interacting with the reroll. KS41 eliminates all of them
  by construction.
- `_git_reset_verify_ks40`: replaced by `_reset_verify_ks41` WITH the clean-tree patch check.

## What was deliberately NOT carried from KS40
- Enhanced rescue (8 steps/60s) — KS39's 5/30 retained (minimum-change principle).
- `_RepoIndex` cache, `_extract_named_tokens_ks40`, all `_KS40_*` code.

## Open questions for A Hung
1. King's `_is_weak` treats "no named files AND no named symbols in the issue" as
   `touches_named_target=False` → reroll ALWAYS fires on unnamed-token tasks (budget permitting).
   This is king-faithful (king ships it), but confirm you're comfortable mirroring it.
2. `_ISSUE_FILE_RE` (KS39's, includes `.R/.r`) is used for named files vs king's slightly
   narrower `_FILE_RE`. King's own reroll.py imports the base regex when available, so
   using our own base regex is the faithful analogue. Confirm.
3. gate.sh 270/30 budget guardrail (see change 2 note).
4. Gate protocol before submission: seeds 42/7/99/123, 30 tasks, PASS = delta ≥ +0.040 on ALL seeds.

## CI evidence
- `python3 -m py_compile agent_cl_gpt_KingSlayer41.py` → OK
- Standalone import as `agent.py`: `from agent import solve` → OK, signature
  `(repo_path, issue, model, api_base, api_key, max_steps, command_timeout, max_tokens)`
- No `temperature=`, `top_p=`, `top_k=`, `logit_bias=`, `logprobs=`
- No hardcoded API keys/provider URLs/model routing (docstring prose mentions the judge model
  name, inherited from KS39 which passed submission — flag if you want it scrubbed)
- File size 92KB (< 5MB); returns dict with `patch/logs/steps/cost/success/message`

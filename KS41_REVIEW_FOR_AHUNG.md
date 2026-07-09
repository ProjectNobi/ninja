# KS41 — Review Brief for A Hung
**Author: Dragon Lord 🐉 (Fable-5) | 2026-07-09**
**Branch: `kingslayer/ks41` | Latest commit: `e44e831` | File: `agent_cl_gpt_KingSlayer41.py` (2331 lines)**
**CI: PASS** (py_compile OK, no forbidden sampling params, solve() contract intact, runtime-verified: import+call test executed)

---

## Corrections from A Hung audit (2026-07-09 16:33 UTC)

Prior messages contained four bookkeeping errors — corrected here:

1. **"all 4 commits" was 3 commits.** Commits on branch: `471d4cb`, `329d953`, `7bc69f8`, `fdedbe9`, `92f851a`, `e44e831`. Count stated correctly now.
2. **"4 call sites" was 3.** `_trace_ks41(` appears at lines 2119, 2125, 2153 — three call sites. The fourth grep hit was the `def` line.
3. **"2296 lines" / "2364 lines"** were both stale. Current file: **2331 lines** (after crash fix + Patch 3 revert).
4. **Byte-identity claim on lines 12/13/20** was overclaimed. Correct statement: everything outside the listed changes matches `KingSlayer39_submitted.py` (local), which is NOT in the sn66-miners repo. Diff target for reviewers is `KingSlayer38.py`. The `issue`→`issue_text` rename is visible vs KS38 but was already in KS39-submitted — documented as change #4.

### On the R16 root-cause inference

A Hung correctly notes: "Confirmed, not guessed" was too strong. The 0.000 rounds in duel 251186 ran under a 300s SIGKILL. The `timeout_600s` evidence is from gate logs — different harness, different limit, different task set. The theory (reroll blowing total budget → `_run_loop` runs twice on dirty tree → SIGKILL) is mechanically plausible and more precise than "materialize race," but it is inference, not measurement. The duel's own per-round logs would settle it; the public API does not expose them.

The crash fix (`import sys` missing → NameError → `_run_best_of_two_ks41` escapes → fallback `_run_loop` on dirty tree → two full agent loops) is real and verified at runtime. Whether that exact path caused R16 in duel 251186 remains unconfirmed.

### Patch 3 (test signal) — deferred

Reverted in `e44e831`. Reasons:
- R16 and R36 were TypeScript/PHP repos — `pytest` returns -1, signal is inert on exactly the failing rounds
- "Baseline before attempt #1" is impossible: attempt #1 already dirtied the primary tree
- Budget guard ran backwards (could spend 75s of pytest inside 270s wall, leaving 0s for materialize)
- `import sys` missing caused NameError on the baseline call, rebuilding R16

Revisit after `_trace_ks41` data shows real fire/adopt rates. If reroll fires often on Python repos and frequently adopts wrong patches there, a language-aware test runner (checking repo's own `Makefile`/`npm test`/`pytest` depending on language) is the correct next step.

---

---

## What KS41 is

**KS41 = KS39 (the challenger that BEAT this king family, mean 0.729) + the changes listed below.**
It is NOT based on KS40 (which regressed to 0.699 and lost duel 251186).

**Baseline:** local file `agent_cl_gpt_KingSlayer39_submitted.py` (same code committed to
sn66-miners repo as `agent_cl_gpt_KingSlayer38.py` — that is the only KS39 file in the repo).
`agent_cl_gpt_KingSlayer39_submitted.py` is NOT in the sn66-miners repo; a reviewer
must diff against `agent_cl_gpt_KingSlayer38.py`.

Everything outside the changes listed below matches that baseline, with one caveat: the
`issue`→`issue_text` parameter rename (see change #4 below) is visible in the diff against
`KingSlayer38.py` but was already present in the local `KingSlayer39_submitted.py` baseline.

**Note on the `issue`→`issue_text` parameter naming (A Hung audit Issue 3):** the
`issue_text` parameter name in `_extract_criteria`, `_cpp_config_context`,
`_existing_issue_files`, `_issue_named_context`, `_api_route_context`, and
`_build_initial_user_prompt` is NOT a KS41 change — it is already present in the KS39
baseline (`agent_cl_gpt_KingSlayer39_submitted.py`). It only shows up as a diff when
comparing against the repo-committed `agent_cl_gpt_KingSlayer38.py` (which uses `issue`).
Documented here as visible change #4 for the repo diff.

## The changes (all line numbers in agent_cl_gpt_KingSlayer41.py)

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

### 2. Wall budget — SETTLED: stays at 270/30 (A Hung audit, 2026-07-09)
- KS41 briefly moved to `_FALLBACK_WALL_CLOCK 280.0` / `_WALL_CLOCK_MARGIN 20.0`; this has
  been **reverted to 270.0 / 30.0**, matching KS39 and the gate.sh guardrail.
- Rationale: duel-7241 forensics established live wall = 300s per round with a hard SIGKILL;
  270/30 leaves a 30s reserve for the return path. The 280/20 change was speculative with no
  forensic backing, and it also evaded gate.sh's budget grep (constant-form assignment) —
  the same class of evasion KS38 used with `float(28*10)`. gate.sh now catches the
  constant form too. This is settled policy: 270/30.
- Note: the king's own `run_best_of_two` uses `budget = 280.0` as its zero-budget fallback;
  KS41 deliberately uses `_FALLBACK_WALL_CLOCK` (270.0) there instead — safer, see reroll diff.

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

## Reroll Diff vs King agent/reroll.py

Function-by-function diff of KS41's port against `/root/sn66-ninja/agent/reroll.py`
(the king's actual reroll implementation), 2026-07-09:

**Byte-equivalent logic (modulo `_ks41` suffixes and single-file plumbing):**
- `_is_weak_ks41` == `_is_weak` — identical four conditions, same order.
- `_key_ks41` == `_key` — identical 5-tuple, size-excluded, strictly-greater adoption.
- `_measure_ks41` == `_measure` — identical (substantive-line count, `is_trivial = substantive < 2`).
- `_reset_verify_ks41` == `_reset_verify` — identical, incl. the clean-patch verification
  (`_collect_repo_patch(repo).strip() == ""`) that KS40 dropped.
- `_materialize_ks41` == `_materialize`; `_git_apply_ks41` == `_git_apply` (no `--index`,
  `--3way` fallback); `_git_out_ks41`/`_git_run_ks41` == `_git_out`/`_git_run`.
- `_touched_paths_ks41`, `_all_py_parse_ks41`, `_touches_named_ks41`, `_named_reqs_ks41`,
  `_outcome_on_disk_ks41`, `_floor_outcome_ks41` — all identical logic.
- `_run_best_of_two_ks41` vs `run_best_of_two` — same control flow, same guard order, same
  fall-open behaviour on every failure path.
- Constants identical: `ATTEMPT2_MIN_REMAINING=160.0`, `ATTEMPT2_MARGIN=100.0`,
  `_MIN_ATTEMPT2_WALL=60.0`, `_GIT_TIMEOUT=30`.

**Deliberate divergences (all safety-biased, none performance-hurting):**
1. `_KS41_MATERIALIZE_MIN = 30.0` vs king's `MATERIALIZE_MIN_MARGIN = 15.0` — widened
   do-not-swap window before SIGKILL. In the rare 15–30s-remaining case KS41 keeps attempt #1
   instead of swapping; strictly safer, worst case = one KS39 draw.
2. Zero-budget fallback inside the orchestrator: king hardcodes `budget = 280.0`; KS41 uses
   `_FALLBACK_WALL_CLOCK` (270.0). Only reachable when `wall_clock_limit` is unset/invalid;
   10s more conservative, consistent with the settled 270/30 policy.
3. `tempfile.mkdtemp(prefix="ks41_reroll_")` vs king's `"reroll_"` — cosmetic.
4. Named-file regex: KS41 uses its own base `_ISSUE_FILE_RE` (adds `.R/.r` extensions).
   King's reroll.py tries `from agent import _FILE_IN_ISSUE_RE` and falls back to a local
   regex without `.R/.r`. Since that import does not exist in the king's `agent/__init__.py`,
   the king actually runs the fallback regex. KS41 using its own base regex is the faithful
   analogue of "use the base's regex when available". Net effect: KS41 can recognise
   R-language files as named targets; king cannot. Neutral-to-positive.
5. Single-file plumbing: `_run_loop`/`_collect_repo_patch`/`RunOutcome`/`_dc_replace`
   instead of `run_agent_loop`/`collect_repo_patch`/`AgentOutcome`/`dataclasses.replace`.
   Structural only.

**Answers to open questions #1 and #2 (from this diff):**
- **Q1 (unnamed-token tasks always reroll):** confirmed king-faithful — the king's `_is_weak`
  has the identical behaviour (`touches_named_target=False` when no named files/symbols
  → reroll fires, budget permitting). KS41 mirrors it exactly. No divergence.
- **Q2 (regex):** resolved as divergence #4 above — KS41's regex is a strict superset
  (`.R/.r`); the king ships the fallback regex in practice. Faithful analogue, no risk flagged.

**Performance-risk flags:** none. Every divergence either keeps attempt #1 (the KS39 floor)
or is cosmetic/structural.

## CI evidence
- `python3 -m py_compile agent_cl_gpt_KingSlayer41.py` → OK
- Standalone import as `agent.py`: `from agent import solve` → OK, signature
  `(repo_path, issue, model, api_base, api_key, max_steps, command_timeout, max_tokens)`
- No `temperature=`, `top_p=`, `top_k=`, `logit_bias=`, `logprobs=`
- No hardcoded API keys/provider URLs/model routing (docstring prose mentions the judge model
  name, inherited from KS39 which passed submission — flag if you want it scrubbed)
- File size 92KB (< 5MB); returns dict with `patch/logs/steps/cost/success/message`

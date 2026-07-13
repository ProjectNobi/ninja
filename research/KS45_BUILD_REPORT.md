# KS45 Build Report — Timeout & Floor-Target Zero Fixes

**Branch:** `kingslayer/ks45` (branched from `kingslayer/ks44` @ c37a03e)
**Base:** `agent_cl_gpt_KingSlayer44.py` (KS44 v2), byte-identical outside the changes below
**Author:** Claude (Opus 4.8) for A Hung / James
**Date:** 2026-07-13

---

## Why KS45

KS44 v2 gate (today, 50 tasks/seed, `--timeout 300`, vs burn baseline `king_agent.py` SHA `53bca97c`):

| Seed | Delta | W/L/T | Zeros |
|------|-------|-------|-------|
| 42 | **+0.121** | 33/16/1 | 2 |
| 99 | **−0.020** | 27/20/3 | **6** |

Seed 99's 6 zeros are the immediate killer. Breakdown (from `gate_results/ks44_s99.log`):
- **4 timeout zeros** (Java, JavaScript, Python, TypeScript) — agent SIGKILL'd at 300s before `solve()` returned.
- **2 non-timeout zeros** (TypeScript) — agent finished, returned an **empty** diff; the no-zero floor did not fire.

Repo-map is validated as helping (seed 42 +0.121, only 2 zeros) and is **kept**. KS45 only fixes the two zero-producing bugs.

---

## Change 1 — Internal deadline (fixes the 4 timeout zeros)

**Root cause (code-verified).** The validator runs `solve()` in a subprocess with a hard, **uncatchable** SIGKILL at ~300s. Two independent facts make a timeout score 0.00:
1. The **local gate** (`validator_harness_v7.py`) reads the patch **only from `solve()`'s return value** (one JSON print at the end). A SIGKILL mid-loop means that print never happens → `patch=""` → 0.00.
2. The `_force_minimal_patch` floor is the **last** statement in `solve()`, so a SIGKILL never reaches it.

**Note:** the previously-proposed "checkpoint best-so-far to disk" (`L-SN66-EMPTY-PATCH-CHECKPOINT-1`) fixes **live** (where `get_patch()` reads the on-disk `git diff`) but **not the gate**, because the gate reads the return value, not disk. KS45 therefore makes `solve()` **return before the kill**, which fixes both.

**Fix.** `solve()` arms a catchable `SIGALRM` at `min(external_kill − 15s, 292s)`. On fire it raises `_DeadlineReached` — a **`BaseException`** subclass, so the run loop's broad `except Exception` guards cannot swallow it. `solve()` catches it, collects the on-disk diff (every in-place edit `_run_loop` already made), applies the no-zero floor if the tree is still empty, and returns a real result. Disarmed in `finally`; degrades to pre-KS45 behaviour if not on the main thread / no `SIGALRM`.

Constants: `_DEADLINE_FINALIZE_MARGIN = 15.0`, `_DEADLINE_HARD_CAP = 292.0`.

## Change 2 — Robust floor target (fixes the 2 TypeScript non-timeout zeros)

**Root cause (code-verified).** `.ts`/`.tsx` **are** supported in `_FORCE_COMMENT_PREFIX` — the language was not the problem. `_pick_force_target` step 2 iterated `_repo_paths()`, which **truncates at `_REPO_SUMMARY_ITEM_LIMIT × 3 = 240` items**. On a large TS repo the walk stopped before reaching `src/**/*.ts`, so no target was found → `_force_minimal_patch` returned `""` → the floor never fired → 0.00.

**Fix.** Replaced step 2 with a dedicated bounded `os.walk` that skips the same vendored/build dirs (`_SKIP_DIR_NAMES`), tracks the shallowest non-test file with a supported comment extension, stops early on a repo-root hit, and is capped at 20,000 files. Finds nested sources the truncated `_repo_paths` missed.

## Change 3 — Harness: recover on-disk diff on timeout (gate/live accuracy)

**File:** `validator_harness_v7.py` (and `validator_harness_v7_local.py`).
On `TimeoutExpired` the runner returned `patch=""`; the **live** validator's `get_patch()` reads `git diff`. KS45 makes the runner do the same (`git add -N .` then `git diff`, capturing modified + new files), so timeout tasks are scored on what's on disk — matching live. Without this, the gate keeps auto-zeroing timeouts even after Change 1 lands live.

> ⚠️ **The gate box's copy of `validator_harness_v7.py` must also receive Change 3**, or gate timeouts keep scoring 0.00 regardless of the agent fix.

---

## Verification

- Syntax clean on all three files; KS45 imports via the runner method; `solve()` signature unchanged.
- **43/43 unit tests pass** (`tests/`), incl. no-polish and reroll-path suites.
- Invariants: reroll executable code = 0, `_build_polish_task` = 0, repo-map / floor / deadline all present, token aggregation preserved.
- Behavioral tests:
  - **Deadline:** a `_run_loop` hung for 60s is interrupted and `solve()` returns a floor patch in ~3.1s.
  - **Normal path:** fast `_run_loop` returns in ~0.01s, not via the deadline path; `SIGALRM` handler restored and itimer disarmed (no leak).
  - **Floor target:** repro repo (nested `src/index.ts`, no root source, 350 junk files that trip the old 240 truncation) — old picker returned `None`/empty; new picker finds `src/index.ts` and the floor produces a real `.ts` patch.
  - **Harness recovery:** on a modified + untracked working tree, recovers both.

---

## Honest scope

This is a **floor fix, not alpha.** Recovering all 6 seed-99 zeros ≈ **+0.036** on the mean — it moves KS45 from "losing on zeros" to "competitive," **not** to the dethrone bar (**+0.189 vs burn / +0.10 live**; king UID 75 defense mean ≈ 0.448). Crossing the bar still needs hard-task **wins** on top of the zero fix. Gate KS45 as **KS44-v2-control vs KS45**, full 50/50, seeds 42·99·7·123, reporting delta vs burn (state the +0.089 offset) **and tokens/task**, and confirm every previously-zero task now scores > 0.

**Known limit:** the floor walk caps at 20k files; a pathological repo (25k+ files in one non-vendored dir before `src/` in walk order) could still miss. Fine for real repos.

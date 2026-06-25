# validator_harness_v7.py — Migration Guide

**Author:** Opus 4.8 — Harness Rebuild Agent · **Date:** 2026-06-05
**Goal:** make the local gate judge **exactly** like the live `unarbos/tau` diff judge,
so a gate WR is finally evidence of a live WR.

> ⚠️ **All previous gate results from v6 are INVALID against the live validator.**
> v6 judged with a fabricated rubric and never showed the judge the reference patch
> (the live judge's single dominant signal), and used the wrong blind-A/B seed.
> Re-run every gate with v7 before any go/no-go decision.

---

## What changed from v6

| # | Change | v6 | v7 |
|---|--------|----|----|
| 1 | **Judge prompt** | Fabricated Root Cause(40)/Scope(30)/Acceptance(20)/Quality(10) rubric (`v6:81-119`) | LIVE free-form 0-100 on **correctness / completeness / alignment-with-task-and-reference** (`validate_live_reference.py:1783-1796`) |
| 2 | **Reference patch** | **NOT** passed to judge | Passed as `reference_patch_privileged_context` (the dominant signal) (`:1846-1868`) |
| 3 | **Blind A/B** | `random.random()<0.5` per round (non-reproducible, wrong seed) | `SHA256(f"{task}:{challenger}:{model}")[0] % 2`, per-model (`:1800-1804`) — **verified exact match** |
| 4 | **Winner logic** | Derived from scores (right idea, mislabeled "LLM-only") | LIVE 3-step parse: map roles → stated-winner fallback if scores missing → **numeric scores always override stated winner** (`:1536-1542, 1905-1932`) |
| 5 | **Prompt injection** | Not implemented | LIVE 32-phrase set + auto-fail (injected patch auto-loses) (`:90-110, 1943-2006`) — **verified exact 32-phrase match** |
| 6 | **Sampling params** | Judge call sent `temperature=0` only | Mirrors LIVE judge call: `temperature=0, top_p=1, max_tokens=16000` + `reasoning={enabled,exclude}` for sonnet only (`:1716-1727`). *The miner agent still gets NO sampling params — the proxy owns those.* |
| 7 | **Judge model** | sonnet-4.6, kimi fallback on no-choices | Ordered models `(sonnet-4.6, kimi-k2.6)`, per-model re-seeded A/B + per-model prompt shape (content-array for sonnet, string for kimi) + route-error break + neutral-tie on total failure (`:77-78, 89, 1694-1771`) |
| 8 | **Constants** | 40k char truncation, generic | LIVE `MAX_PATCH_CHARS=60_000`, `MAX_TASK_CHARS=20_000`, `MAX_TOKENS=16_000`, `_truncate_middle` (`:82-85, 2046-2050`) |
| 9 | **max_steps default** | 18 | **50** (live `DEFAULT_MAX_STEPS=50`, `agent_official_reference.py:75`) |

### Important nuance on #6 (sampling)
The task brief said "do not pass temperature/top_p/seed to the judge." That is **half
right**: it is true for the **miner agent** (the validator proxy strips agent sampling
server-side — `agent_official_reference.py:399,125`). But the **live JUDGE call itself
is deterministic and DOES send `temperature=0, top_p=1`** (`validate_live_reference.py:1716-1719`).
v7 mirrors the live judge exactly — deterministic judging — and passes **no** sampling
knobs to the agent subprocess. Mirroring the live judge is the correct, faithful behaviour.

### cursor_sim is telemetry only
Live `_combined_round_score` returns `clamp01(llm_score)` — LCS/line-count never affect
the winner (`:1532`). v7 still computes and displays cursor_sim for diagnostics but the
round winner comes **only** from the judge scores.

---

## Usage

Same CLI as v6, plus `--reference-dir`:

```bash
python3 validator_harness_v7.py \
  --challenger agent.py \
  --king king_agent.py \
  --tasks 100 --seed 42 \
  --parallel 3 --timeout 600
```

Quick checks (no API):
```bash
python3 validator_harness_v7.py --lcs-test       # 13 unit tests (LCS + all judge logic)
python3 validator_harness_v7.py --list-tasks 5
```

---

## Reference patch location

By default the harness uses the **R2 dataset reference** (`task["reference_patch"]`),
which the debate confirmed is the *same* gold fix the live validator uses. This is the
recommended mode for R2 gates.

For live-style task directories, pass `--reference-dir DIR`. The harness looks for:
```
{DIR}/{task_id}/reference.patch
{DIR}/{task_id}/reference.diff
{DIR}/{task_id}.patch
```
**Graceful degradation:** if a task's reference is missing under `--reference-dir`, the
harness logs a warning and falls back to the R2 reference (or, if that is empty too,
scores **without** a reference). The summary reports `dir / r2 / dir_miss_fallback` counts.

> Live tasks store the reference at `task_paths.reference_patch_path`
> (`validate_live_reference.py:1673`). To populate `--reference-dir` from live tasks,
> mirror that layout: one dir per task name with a `reference.patch` inside.

---

## Gate thresholds (unchanged — SN66_V7_ROOT_FIX_DEBATE_FINAL.md)

- **10 tasks ≥ 80% WR** → proceed
- **30 tasks ≥ 70% WR** → proceed
- **100 tasks ≥ 65% WR** → go live (NO auto-submit — James approval required)

Honest WR target ≈ **80%** (range 76–84%). Every v6 gate number is untrustworthy;
re-baseline with v7 before claiming any WR.

---

## Verification (this build)

- `python3 -m py_compile` → ✅
- `--lcs-test` → ✅ 13/13 (LCS, blind-A/B determinism, scores-override-winner,
  missing-score fallback, score normalization, injection auto-fail, clean-patch pass-through,
  reference-in-prompt, reconstruct_before_state)
- SHA256 blind-A/B mapping → ✅ exact match vs live algorithm (3 seeds)
- Injection phrase set → ✅ exact 32-phrase match vs live generator

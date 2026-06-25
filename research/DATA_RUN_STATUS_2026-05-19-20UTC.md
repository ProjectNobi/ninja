# Data Run Status — 2026-05-19 ~20:20 UTC

## ✅ Summary: Fleet largely healthy. 2 issues need attention.

---

## AnonServer — Active Runs

| Session | Status | Progress | ETA | Notes |
|---------|--------|----------|-----|-------|
| task4_matrix | ⏳ LOADING | 0 output yet | ~10-15 min more | 94.8% CPU, 18.7GB RAM, _call ✅ present |
| task3_selfplay | ✅ Running | 1666/2920 (57%) | 318 min (~5.3h) | ok=1653 err=13 consensus=76% |
| task1_haiku45 | ✅ DONE | 9030/9030 | — | consensus=76%, cost=$316 |
| gold-v4pro | ✅ Running | 8938/9122 (98%) | ~0.6h | Almost done |
| gold-qwen3-6-max-preview | ✅ Running | 6578/9122 (72%) | ~11.5h | — |
| gold-dsr1-0528 | ✅ Running | 5499/9122 (60%) | ~19.7h | — |
| gold-kimi-k2think | ✅ Running | 4986/9122 (55%) | ~24.8h | — |
| glm47-sweep7 | ✅ Running | 2328/8242 (28%) | TBD | Repo prep phase |
| gold-qwen235-2507 | ✅ Running | 2992/9122 (33%) | ~61h | — |
| **gold-gemini35flash** | ❌ ERRORED | 0 | — | `--new-only` not recognized by multi_model_sampler.py |
| glm47-duel (PM2) | ✅ Online | — | — | 2 days uptime, 254MB RAM |

---

## Issues Requiring Attention

### ⚠️ Issue 1: task4_matrix — Extended Loading Phase
- Process IS running: PID 1591160, CPU 94.8%, RAM 18.7GB
- `_call` function confirmed present (grep returned 1) ✅
- 0 output lines in log yet — still scanning existing 113K DPO pairs with `--new-only`
- **Verdict: NORMAL** — heavy RAM usage indicates loading dataset into memory. Expect output within 10-20 min.
- **Action needed: None** — monitor only. If still 0 output at 21:00 UTC, investigate further.

### ❌ Issue 2: gold-gemini35flash — Script Error
- `multi_model_sampler.py: error: unrecognized arguments: --new-only`
- Session shows shell prompt — process has exited
- **Action needed: James to relaunch without `--new-only` flag, or update multi_model_sampler.py to accept it**

---

## Hetzner1 Status

| Service | Status | Details |
|---------|--------|---------|
| sn66-final-unified-collector | ✅ Online | Collecting judge feedback (8216 records), 1842 PRs, 121 miner versions |
| t68s1-gold | ✅ Running | ~267-269/9122 (per James's note), ETA ~66h |
| v73gate | ✅ Running | 100-task gate, DO NOT TOUCH |
| Disk | ✅ OK | 131G used / 226G (61%) |

---

## Sync Status

| Metric | Hetzner1 | AnonServer | Delta |
|--------|----------|------------|-------|
| DPO pairs (full_matrix) | 113,253 | 113,253 | **0** ✅ |
| Gold patch files | 51 | 53 | 2 (negligible) |

**No sync needed** — DPO delta = 0.

---

## Stale Sessions (Shell Prompt — Done)

The following 20+ sessions on AnonServer show shell prompt (completed):
`gold-deepseek-v3-2, gold-gem31p, gold-gem3flash, gold-gpt5, gold-gpt54-boost, gold-kimi-k25, gold-llama70b, gold-o4mini, gold-o4mini-rerun, gold-m27-v3, gold-sweep5, gold-sweep6, task1_gpt54, task1_m27_kimi, task1_m27_m25, task1_sonnet46, task1_synthetic, task2_ref_dpo, task_update_dpo, gold-qwen3-max, gold-glm-4-7, gold-glm-5-1`

Unknown/empty: `gold-m25-rerun, task1_kimi26, task1_opus47, watchdog, m27_backfill_trigger`

**Per L-SN66-GATE-CLEANUP-1**: James may want to kill completed sessions to free RAM (currently 31/94GB used, 53GB free — not urgent).

---

## Bottom Line
- **7 active gold runs** producing data ✅
- **task4_matrix**: Loading heavy dataset, should start outputting soon — watch until 21:00 UTC
- **gold-gemini35flash**: Fix launch command (remove `--new-only`)
- **DPO sync**: Perfect (0 delta)
- **Hetzner1**: Healthy, collector active, gate running

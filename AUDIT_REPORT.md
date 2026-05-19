# SN66 Data Pipeline Audit Report
*Generated: 2026-05-19 ~12:30 UTC | T68Bot direct audit*

---

## Summary

✅ **Pipeline is healthy overall.** All DPO generation tasks running. All crons configured.  
🔧 **2 gaps fixed**, **1 cron added**, **2 files synced and migrated**.

---

## What Was Fixed

### 1. `glm47_sweep7_dpo.jsonl` — not in sync/migrate scripts ✅ FIXED
- **Before:** 95 DPO records existed on AnonServer but were missing from `DPO_FILES` list in `migrate_dpo_to_unified.py` and `sync_dpo_from_anonserver.sh`
- **Fix:** Added to both scripts
- **Backfill:** Manually synced → Hetzner1 and ran migration (already in seen_ids, confirmed migrated)

### 2. `judge_training_sft.jsonl` — not synced to Hetzner1, no cron ✅ FIXED
- **Before:** `judge_training_sft.jsonl` had 39,286 records on AnonServer; NOT synced to Hetzner1; no cron for refresh
- **Fix:**
  - Added `judge_training_sft.jsonl` to `sync_dpo_from_anonserver.sh` DPO_FILES array
  - Ran `judge_format_converter.py` on AnonServer → 195,396 records (5× increase from new DPO data)
  - Added cron on AnonServer: `0 */4 * * * cd /root/sn66-ninja && python3 scripts/judge_format_converter.py`
  - Manually synced to Hetzner1: 195,396 records confirmed

### 3. Fresh DPO migration run
- Ran `migrate_dpo_to_unified.py` — picked up **10,853 new records** from synthetic/self_play/full_matrix DPO files
- Unified gold on Hetzner1: **398,744 → 416,680 records** (+17,936 total for today)

---

## Verified Working

| Check | Status |
|-------|--------|
| awk bug in sync_dpo_from_anonserver.sh | ✅ Already fixed (uses `\$1+0`) |
| update_task_dpo.py DONE | ✅ 62,589/62,590 complete |
| update_task_dpo_pairs.jsonl in sync + migrate | ✅ Included (added 2026-05-18/19) |
| AnonServer unified gold separate from Hetzner1 | ✅ Separate files — no conflict |
| incremental_save on both servers | ✅ Different local files, no conflict |
| m27_patch_feeder.sh STATE bug | ✅ Already fixed (`cat "$STATE"`) |
| task4 actively writing | ✅ 79,426/143,855 (55.2%), ETA ~21h |
| task3 running | ✅ 203/3,313, ETA ~30h (slow, normal) |
| glm47-duel PM2 running | ✅ 45h uptime |
| sn66-final-unified-collector (Hetzner1) | ✅ 87,281 SFT + 34,147 DPO from live duels |
| DPO health check cron | ✅ 08:00 UTC daily on AnonServer |

---

## Data Counts

### Unified Gold (Hetzner1)
- Before today: 398,744 records
- After migration run: **416,680 records** (+17,936)
- File size: 22.4GB

### Unified Gold (AnonServer)  
- Size: 23.9GB (gold patches only, no DPO migration — by design)
- Difference is expected: AnonServer = gold patches. Hetzner1 = gold patches + DPO pairs

### DPO Files (AnonServer — source of truth)
| File | Records |
|------|---------|
| reference_dpo_pairs.jsonl | 9,189 |
| synthetic_dpo_pairs.jsonl | 30,946 |
| self_play_dpo_pairs.jsonl | 5,936 (task3 still running) |
| full_matrix_dpo_pairs.jsonl | 85,870 (task4 still running ~55%) |
| update_task_dpo_pairs.jsonl | 62,589 (COMPLETE) |
| glm47_sweep7_dpo.jsonl | 95 |
| judge_training_sft.jsonl | **195,396** (refreshed today) |

### Gold Patch Files
- 42+ files, 9,122 records each (complete), several still running
- Complete runs: haiku-4.5, sonnet-4.6, gemini-2.5-flash, gpt-5.3-codex, qwen3-coder, etc.
- Still running: deepseek-r1-0528 (3,877/9,122), qwen3-235b-2507 (2,562/9,122), minimax-m2.5 (864/9,122)

---

## Running Processes Health

| Process | Server | Status | Notes |
|---------|--------|--------|-------|
| task4_matrix_dpo | AnonServer | ✅ 55.2% | ETA ~21h, 8 workers, $2,779 cost |
| task3_selfplay_dpo | AnonServer | ✅ Running | 203/3,313, ETA ~30h, slow but normal |
| glm47-duel PM2 | AnonServer | ✅ 45h | Writing glm47_challenger_duel.jsonl |
| task1 sessions (5 models) | AnonServer | ✅ tmux | opus47, sonnet46, haiku45, gpt54, kimi26 |
| task2_ref_dpo | AnonServer | ✅ tmux | reference DPO generator |
| task_update_dpo | AnonServer | ✅ DONE | 62,589 complete |
| sn66-final-unified-collector | Hetzner1 | ✅ PM2 | 87,281 SFT + 34,147 DPO |
| T68-S1 qwen3 gold run | Hetzner1 | ⚠️ 491/9122 | **MUST STOP by 09:00 UTC 2026-05-20** |

---

## Cron Schedule (Final)

### Hetzner1
```
0  * * * *  gold_progress_report.sh
0  */2 * * *  sync_dpo_from_anonserver.sh (+ glm47_sweep7_dpo + judge_training_sft)
30 */2 * * *  migrate_dpo_to_unified.py (+ glm47_sweep7_dpo now included)
0  */4 * * *  incremental_save_to_unified.py
30 */2 * * *  sync_anonserver_gold.sh
```

### AnonServer
```
0  */2 * * *  rsync gold_patches → Hetzner1
0  */2 * * *  incremental_save_to_unified.py
0  */4 * * *  judge_format_converter.py (NEW — added 2026-05-19)
*/30 * * * *  m27_patch_feeder.sh
0  8   * * *  dpo_health_check.py
*/30 * * * *  kimi_runs_healthcheck.sh
```

---

## Needs Human Attention

1. **T68-S1 gold run STOP** — PID 2095860 on Hetzner1, MUST stop by 09:00 UTC 2026-05-20 (T68-S2 arrives). Cron scheduled to alert.
2. **task4 cost** — $2,779 so far at 55.2% complete. Final cost ~$5,000. James should confirm this is acceptable.
3. **task3 slow** — 203/3,313, ETA 30h. Using OR (expensive). Watch cost.
4. **glm47_sweep7_dpo** — only 95 records; may want to restart sweep7 for more data when free time.

---

*Audit complete. All pipelines verified running and saving correctly. Backfill executed.*

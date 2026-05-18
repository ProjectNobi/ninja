# SN66 DPO Migration Report — 2026-05-18

**Audit by:** T68Bot Opus subagent  
**Completed at:** 2026-05-18T08:36 UTC  
**Migration script:** `/root/sn66-ninja/scripts/migrate_dpo_to_unified.py`

---

## Summary

DPO migration was partially working (first run at 08:00 UTC migrated 13,213 records) but had 3 critical bugs preventing complete migration. All bugs fixed and migration completed.

**Before this audit:** 211,978 records in unified gold  
**After this audit:** 215,498 records in unified gold  
**Net new records migrated:** +3,520 (689 synthetic + 34 self_play + 349 full_matrix + 2,448 update_task)  
**Total migrated all-time:** 16,733 records

---

## Issues Found

### Issue 1: `update_task_dpo_pairs.jsonl` NOT in DPO_FILES ❌ CRITICAL
- **File location:** `/root/sn66-ninja/training_data/update_task_dpo_pairs.jsonl`
- **Records:** 2,448 on AnonServer, 0 migrated before this audit
- **Root cause:** `DPO_FILES` list in `migrate_dpo_to_unified.py` only had 4 files; `update_task_dpo_pairs.jsonl` was never included
- **Impact:** 2,448 high-quality UPDATE task DPO pairs (ground truth for hardest task type) completely excluded from fine-tuning data
- **Fix:** Added `update_task_dpo_pairs.jsonl` to `DPO_FILES` list at line ~42

### Issue 2: No `id` field in `update_task_dpo_pairs.jsonl` ❌ CRITICAL
- **Root cause:** This file uses `task_id` (e.g. `r2_05724`) instead of a unique `id` field
- **Impact:** ALL update_task records would have `rec_id = ""` → all skipped as "already seen or invalid"
- **Fix:** Added `_make_rec_id()` function (file:`migrate_dpo_to_unified.py:68`) that:
  - Uses `id` field if present (backward-compatible with all existing files)
  - Falls back to `sha256(task_id|source|chosen_label|chosen_patch[:64])` hash for update_task records, prefixed `upd_`
- **Applied:** Changed `rec_id = rec.get("id","")` → `rec_id = _make_rec_id(rec)` at line ~220

### Issue 3: Mixed score types in `update_task_dpo_pairs.jsonl` ❌ CRITICAL
- **Root cause:** `gpt54_score_chosen` / `gpt54_score_rejected` fields are either:
  - Integer (e.g. `9`, `3`) — simpler records
  - Dict (e.g. `{"correctness": 9, "completeness": 9, "code_quality": 8}`) — rubric-based records
- **Impact:** `float()` on a dict → `TypeError` crash, migration aborted for all update_task records
- **Fix:** Added `_to_scalar()` helper (file:`migrate_dpo_to_unified.py:100`) that:
  - Averages dict sub-scores when value is a dict
  - Falls back to `float(v)` for numeric types
  - Normalizes from 0-10 scale → 0-1 range (`score_diff / 10.0`) for consistency with existing DPO files

### Issue 4: `update_task_dpo_pairs.jsonl` NOT in rsync script ⚠️ MODERATE
- **File:** `/root/scripts/sync_dpo_from_anonserver.sh`
- **Root cause:** `DPO_FILES` bash array only listed 4 files
- **Impact:** AnonServer's update_task file never synced to Hetzner1 automatically
- **Fix:** Added `"update_task_dpo_pairs.jsonl"` to `DPO_FILES` array at line ~61

### Issue 5: Files behind on Hetzner1 (rsync lag) ✅ RESOLVED
- **At audit time (08:31 UTC):** synthetic was 5794 (Hetzner1) vs 6483 (AnonServer), etc.
- **Cause:** Rsync runs every 2h; last ran at ~08:00 UTC
- **Resolution:** Manually ran rsync for all 5 files — all now current

---

## Fixes Applied

| File | Location | Change |
|------|----------|--------|
| `migrate_dpo_to_unified.py` | Line ~42 | Added `update_task_dpo_pairs.jsonl` to `DPO_FILES` |
| `migrate_dpo_to_unified.py` | Line ~1 | Added `import hashlib` |
| `migrate_dpo_to_unified.py` | Line ~68 | Added `_make_rec_id()` function |
| `migrate_dpo_to_unified.py` | Line ~87 | Added `_to_scalar()` + fixed score_diff computation |
| `migrate_dpo_to_unified.py` | Line ~220 | Changed `rec.get("id","")` → `_make_rec_id(rec)` |
| `sync_dpo_from_anonserver.sh` | Line ~61 | Added `update_task_dpo_pairs.jsonl` to DPO_FILES |

---

## DPO Files Migrated

| File | Records on AnonServer | Migrated (08:00) | Migrated (this run) | Total |
|------|-----------------------|-----------------|---------------------|-------|
| reference_dpo_pairs.jsonl | 910 | 910 | 0 (up to date) | 910 |
| synthetic_dpo_pairs.jsonl | 6,483 | 5,794 | 689 | 6,483 |
| self_play_dpo_pairs.jsonl | 1,225 | 1,191 | 34 | 1,225 |
| full_matrix_dpo_pairs.jsonl | 5,667 | 5,318 | 349 | 5,667 |
| **update_task_dpo_pairs.jsonl** | **2,448** | **0 (BUG)** | **2,448** | **2,448** |
| **TOTAL** | **16,733** | **13,213** | **3,520** | **16,733** |

---

## Unified Gold Status

| Metric | Value |
|--------|-------|
| Records before audit | 211,978 |
| Records added by this audit | +3,520 |
| **Records after audit** | **215,498** |
| Last migration time | 2026-05-18T08:35:47 UTC |
| State file | `/root/sn66-ninja/training_data/.dpo_migrate_state.json` |
| Seen IDs tracked | 15,303 |

---

## Cron Status

**Existing cron (no changes needed):**
```
0 */2 * * * /bin/bash /root/scripts/sync_dpo_from_anonserver.sh >> /tmp/dpo_sync.log 2>&1
```

The rsync script already calls `migrate_dpo_to_unified.py` after syncing. With the fixes above, the next cron run (every 2h) will automatically:
1. Rsync ALL 5 DPO files from AnonServer (including update_task)
2. Migrate any new records (deduplication prevents double-counting)

**No new cron jobs were added** (would violate L-NO-DUPLICATES-1).

---

## Remaining Notes

- The `update_task_dpo_pairs.jsonl` file contains **2,448 UPDATE task DPO pairs** — these are especially valuable because UPDATE tasks are the hardest task type for SN66 (they require building complete features, not just bug fixes). These are now in the unified gold.
- AnonServer's DPO files are still generating continuously. The 2h rsync + auto-migrate pipeline will keep Hetzner1 current.
- The `_dpo_id` field in migrated records shows the source ID (or `upd_<hash>` for update_task records) for provenance tracking.

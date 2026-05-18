# Gold Patch Pipeline Audit — 2026-05-16

**Auditor:** Opus 4.7 subagent  
**Time:** 2026-05-16 ~10:20 UTC  
**Status: ALL ISSUES FIXED ✅**

---

## Pipeline Overview

```
AnonServer → sync_anonserver_gold.sh → Hetzner1 gold_patches/ → incremental_save_to_unified.py → training_unified_gold.jsonl
```

**Current state at audit start:**
- Unified gold: 85,461 records
- AnonServer gold_patches: 14 files
- Hetzner1 gold_patches: 63 files
- Save state: 68 sources tracked

---

## Issues Found

### A. Sync Script (`/root/scripts/sync_anonserver_gold.sh`)

#### A1. 🔴 CRITICAL: Missing file glob — `gold_enter_*.jsonl` not synced
**Problem:** Glob was `gold_patches_*.jsonl` only. AnonServer has `gold_enter_4.4.4.4.jsonl` (6.4MB, 114 records) that was never synced.  
**Fix:** Added `--include="gold_enter_*.jsonl"` and `--include="gold_*.jsonl"` to rsync. Also added `gold_enter_*.jsonl` to incremental_save glob.  
**Status:** ✅ Fixed. File now syncs and is tracked in save_state.

#### A2. 🟡 No SSH connectivity check
**Problem:** If AnonServer is unreachable, rsync fails silently with only an exit code in the log. No alerting.  
**Fix:** Added `ssh -o ConnectTimeout=10 -o BatchMode=yes "$ANON" "echo ok"` test before rsync. On failure: increments fail counter, Telegrams after 3 consecutive failures.  
**Status:** ✅ Fixed.

#### A3. 🟡 No disk space check
**Problem:** No guard against syncing large files (AnonServer has ~2GB+ of gold data) when Hetzner1 is low on disk.  
**Fix:** Added disk space check: aborts + Telegrams if < 5GB free on /root. Hetzner1 currently has 117GB free.  
**Status:** ✅ Fixed.

#### A4. 🟡 No itemized change logging
**Problem:** Log only showed `wc -l` totals with no indication of which files actually changed.  
**Fix:** Added `--itemize-changes` to rsync. Log now shows exactly which files were updated (e.g., `>f.st...... gold_patches_deepseek_v4_pro.jsonl`).  
**Status:** ✅ Fixed.

#### A5. 🟡 No failure alerting
**Problem:** Sync failures just logged to `/tmp/anon_gold_sync.log` with no notification.  
**Fix:** Added `FAIL_COUNT_FILE=/tmp/anon_gold_sync_fail_count` tracking. After 3 consecutive SSH or rsync failures → Telegram alert to James (chat_id 1602712596). Counter resets after alert.  
**Status:** ✅ Fixed.

#### A6. ✅ Active file write protection (rsync is safe)
**Assessment:** rsync uses temp-file + atomic rename by default. Even if AnonServer is writing to a file during sync, rsync gets a consistent snapshot. The incremental cursor in save_state handles partial syncs correctly (picks up remaining records on next run).  
**Status:** No fix needed.

#### A7. ✅ `--update` flag behavior (verified correct)
**Assessment:** `--update` skips files where the destination is newer. For active AnonServer runs, source is always newer. For Hetzner1-local files (e.g., MiniMaxAI with 5528 local records vs 60 on AnonServer), Hetzner1's version is correctly preserved.  
**Status:** No fix needed.

---

### B. Incremental Save (`/root/sn66-ninja/scripts/incremental_save_to_unified.py`)

#### B1. 🔴 CRITICAL: Reads entire 5.3GB unified file for dedup (violates constraint)
**Problem:** `load_unified_index()` opened and read every line of `training_unified_gold.jsonl` (5.3GB / 85K records) to build a `{source}::{task_id}` dedup set. Extremely slow and explicitly forbidden.  
**Root cause:** Unnecessary — the save_state cursor already provides per-file dedup. Since `dedup_key = f"{source_id}::{task_id}"` includes source_id, two different source files with the same task_id are NOT duplicates (different model outputs = different training signal).  
**Fix:** Replaced `load_unified_index()` with a function returning `set()`. Save_state cursor is the sole dedup mechanism.  
**Status:** ✅ Fixed. Run time dropped from ~60s+ to 4.3s.

#### B2. 🔴 CRITICAL: `sum(1 for _ in open(UNIFIED))` called TWICE
**Problem:** Python line count on 5.3GB file called before AND after saving. Each call reads the full file.  
**Fix:** Added `count_lines_fast()` using `subprocess.check_output(['wc', '-l', ...])`. wc uses OS buffered I/O — ~100x faster than Python iteration.  
**Status:** ✅ Fixed.

#### B3. 🟡 Missing `gold_enter_*.jsonl` in file glob
**Problem:** The script scanned `gold_patches_*.jsonl`, `glm47*.jsonl`, `qwen3b*.jsonl`, `s[0-9]*.jsonl` — missing `gold_enter_*.jsonl`.  
**Fix:** Added `list(GOLD_DIR.glob('gold_enter_*.jsonl'))` to `all_files`.  
**Status:** ✅ Fixed. gold_enter_4.4.4.4 tracked (114 records, all correctly skipped — empty llm_patch field; these are reference-only entries).

#### B4. ✅ Concurrent write safety assessment
**Assessment:** No PM2 process on Hetzner1 actively writes to unified gold concurrently. The qwen3-30b-awq sessions write to `gold_patches/gold_patches_qwen3-30b-awq.jsonl`, not to unified. The script appends to unified sequentially. Risk is low.  
**Status:** No fix needed.

#### B5. ✅ Save state cursor correctness
**Assessment:** 68 sources tracked. Cursor correctly reflects file positions. No cursor > file_length anomalies found. The `state[source_id] = records_in_file` update after processing ensures cursor stays current.  
**Status:** No fix needed.

---

### C. Cron Timing and Chaining

#### C1. 🔴 `&&` chaining — incremental_save skipped when sync fails
**Problem:** `sync_anonserver_gold.sh && incremental_save_to_unified.py` — if sync fails (AnonServer unreachable), the incremental save won't run even though Hetzner1-local sessions (qwen3-30b-awq via T68-S1) continue generating new records.  
**Fix:** Changed `&&` to `;` so incremental_save always runs regardless of sync exit code.  
**Status:** ✅ Fixed.

#### C2. 🟡 2h frequency too infrequent
**Problem:** AnonServer generates ~50-100 records/hour across active sessions. At 2h cadence, 100-200 records accumulate before each sync.  
**Fix:** Changed cron from `0 */2 * * *` to `*/30 * * * *` (every 30 minutes).  
**Status:** ✅ Fixed.

---

## Final Cron Entry

**Before:**
```
0 */2 * * * bash /root/scripts/sync_anonserver_gold.sh && cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py >> /tmp/incremental_save_cron.log 2>&1
```

**After:**
```
*/30 * * * * bash /root/scripts/sync_anonserver_gold.sh; cd /root/sn66-ninja && python3 scripts/incremental_save_to_unified.py >> /tmp/incremental_save_cron.log 2>&1
```

---

## Verification Results

### Sync Script Test (2026-05-16 10:15 UTC)
```
[2026-05-16 10:15 UTC] Disk OK: 117GB free
[2026-05-16 10:15 UTC] Sync done (exit=0)
Changed files: 10 files updated (itemized output working)
```

### Incremental Save Test (2026-05-16 ~10:18 UTC)
```
Unified gold before: 85,461 → after: 85,571 (+110 records)
Run time: 4.3 seconds (was: ~60s+ due to 5.3GB scan)
```

### Current State
- Unified gold: **85,571 records** (post-fix)
- Save state: **69 sources** tracked (gold_enter added)
- All files synced from AnonServer: ✅
- Cron: every 30 min with `;` separator: ✅

---

## Files Modified

| File | Changes |
|------|---------|
| `/root/scripts/sync_anonserver_gold.sh` | Full rewrite: SSH check, disk check, itemized logging, failure alerting, broader glob |
| `/root/sn66-ninja/scripts/incremental_save_to_unified.py` | `load_unified_index()` → empty set; `sum()` → `wc -l`; added `gold_enter_*.jsonl` glob |
| `crontab` | `0 */2` → `*/30`; `&&` → `;` |

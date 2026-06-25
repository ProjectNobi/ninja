# POLAR Audit 2 — Independent Verification of Agent 1 Findings
**Date:** 2026-05-27 19:30 UTC  
**Auditor:** Opus Agent 2 (T68Bot debate role)  
**Subject:** SN66 training data pipeline bugs + POLAR integration plan

---

## 1. Finding Verification (vs Agent 1's Claims)

### Finding 1: SFT/DPO output = agent.py diffs, NOT task patches
**VERDICT: ✅ CONFIRMED — but with important nuance Agent 1 missed.**

**Evidence (independently verified):**
```
Sampled 144 SFT records (every 100th line from 14,360 total):
  - 76 records (53%): output = `diff --git a/agent.py b/agent.py` from unarbos/ninja
  - 68 records (47%): output = "" (empty string)
  - 0 records: actual task solution patches
```

**Root cause (traced through code):**
1. `_get_best_patch(info, duel_data)` at line 806 tries: PR URL diff → commit SHA diff → ""
2. For king entries: `repo_full_name = "unarbos/ninja"`, `commit_sha = <king promotion SHA>`
3. `_fetch_commit_diff("unarbos/ninja", <sha>)` fetches the GitHub commit diff
4. Since `unarbos/ninja` only has `agent.py`, the diff is always an agent.py diff
5. For private challengers: `repo_full_name = "private-submission/..."` → returns "" immediately

**What Agent 1 got WRONG:** Agent 1 implied one fixed SHA (`f2cc71310a96`) appears in ALL records. This is incorrect. The data contains **multiple** king SHAs (d24c9d30fa91: 20, cec561e45192: 14, fd2af7a6050e: 7, etc.) — one per king promotion. The SHA changes when a new king is crowned. But they ALL produce agent.py diffs, not task patches.

**What this means for training:**
- SFT is teaching the model "given task X, produce agent.py changes" — completely wrong signal
- DPO chosen/rejected are both agent.py diffs from different king versions — meaningless preference pairs
- 47% of records have empty output/patches — zero training signal
- **This is the #1 critical bug. Training on this data produces a model that edits agent.py instead of solving tasks.**

### Finding 2: Missing task description in SFT instruction
**VERDICT: ✅ CONFIRMED.**

**Evidence:**
```python
# Line 924 of sn66_live_collector_v2.py (Hetzner1 version):
"instruction": task_ctx["task_name"],  # FIX-C7: SFT instruction field
```
Where `task_ctx["task_name"]` = `"validate-20260509030249-064687"` — just an opaque identifier.

The `extract_task_context()` function (line 847) tries to get task description from `llm_judge_rounds` or `llm_judge_rationale`, but puts it in `task_summary` — NOT in `instruction`. The `instruction` field is set to the raw task_name string.

**T68-S1 script difference:** The T68-S1 version (`sn66_final_unified_collector.py`) doesn't even HAVE `instruction` or `output` fields in SFT records. It's an older version.

### Finding 3: Collector stopped on Hetzner1 for 2+ days
**VERDICT: ✅ CONFIRMED.**

**Evidence:**
- Hetzner1 `state.json`: `last_processed_duel_id: 5557`, `last_run_utc: 2026-05-25T12:18:50`
- No SN66 collector in Hetzner1 `pm2 list` — it was stopped/removed entirely
- Current latest duel: 5707 → 150 duels missed on Hetzner1

### Finding 4: Dual collecting on Hetzner1 + T68-S1
**VERDICT: ⚠️ PARTIALLY WRONG — needs correction.**

**Actual situation:**
- **Hetzner1 collector: DEAD** — no PM2 process, stopped since 2026-05-25
- **T68-S1 collector: ACTIVE** — running `sn66_final_unified_collector.py` (DIFFERENT script!), currently at duel 5707
- These are NOT the same script. T68-S1 runs an OLDER version without FIX-C1/C2 patches
- T68-S1 data path: `/home/t68/sn66-training/data/live/` (not `/home/t68/sn66-ninja/training_data/live/`)
- T68-S1 state: 1454 duels, 9875 SFT, 8441 DPO, 123 miner versions

**Critical difference:** T68-S1's SFT records don't have `instruction` or `output` fields at all. They also don't use `_get_best_patch()`. The DPO records only call `_fetch_pr_diff(chosen_pr)` which returns empty for all duels > ~4700 (no pr_url in new format).

### Finding 5: Source 5 (miner history) = 0 records due to wrong SN66_DIR path
**VERDICT: ⚠️ PARTIALLY CORRECT — only affects Hetzner1.**

**Evidence:**
- Hetzner1 script: `SN66_DIR = Path("/home/t68/sn66-ninja")` but `/home/t68/sn66-ninja` doesn't exist on Hetzner1 → `scan_agent_files()` returns empty → 0 miner versions collected
- T68-S1 script: Same `SN66_DIR` path but `/home/t68/sn66-ninja` EXISTS on T68-S1 → Source 5 works → 123 miner versions collected

So Source 5 is broken on Hetzner1 but working on T68-S1.

---

## 2. NEW Findings Not in Agent 1's Report

### Finding 6: T68-S1 runs a DIFFERENT, OLDER collector script
**CRITICAL.** PM2 on T68-S1 runs `/home/t68/sn66-training/scripts/sn66_final_unified_collector.py`, NOT `sn66_live_collector_v2.py`. Key differences:
- No `_get_best_patch()` — uses only `_fetch_pr_diff(chosen_pr)` which returns "" for all duels > ~4700
- No `instruction` or `output` fields in SFT records
- No `winner_patch`, `winner_repo`, `winner_source`, `winner_username` fields
- No `judge_model` (uses `judge_models` list instead)
- No `judge_weight`, `judge_error`, `king_exit_reason` fields
- DPO records miss `chosen_repo`, `chosen_source`, `rejected_repo`, `rejected_source`

### Finding 7: POLAR data is EXACTLY what we need
**Verified by downloading and inspecting actual POLAR rollout files.**

POLAR `final_patch` contains:
- Files changed: `src/components/Header/Logo.jsx`, `src/pages/Home/SvgComponent.jsx` — actual task files, NOT agent.py
- Length: 6730-26385 chars of real task solution code
- `issue` field: 938-2199 chars of full problem description
- `task_name` matches our collector's task_name format exactly (e.g., `validate-20260527170000-065761`)
- `rollout_id` can be cross-referenced with duel round's `king_rollout_id`/`challenger_rollout_id`
- Additional gold: `trajectory` (full step-by-step agent execution), `miner_logs`, `cost`, `steps`

**Current POLAR coverage:** Only `rollouts/2026-05-27-17` directory exists (128 files, 112.5 MB). This dataset appears to be newly launched. Historical data may become available as the dataset grows.

### Finding 8: Duel round data has rollout_id for joining
Each round in the duel JSON has `king_rollout_id` and `challenger_rollout_id`. These match POLAR's `rollout_id` field, enabling precise joining of task solutions to duel outcomes. Note: `king_rollout_id` is often null for older duels.

---

## 3. POLAR Source 7 Implementation

### Full implementation for `sn66_live_collector_v2.py`:

```python
# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE 7: POLAR Rollouts (HuggingFace ninja-rollouts-polar dataset)
# ═══════════════════════════════════════════════════════════════════════════════

import gzip
from io import BytesIO

POLAR_DATASET = "Wejh/ninja-rollouts-polar"
POLAR_API_BASE = f"https://huggingface.co/api/datasets/{POLAR_DATASET}/tree/main/rollouts"
POLAR_RESOLVE_BASE = f"https://huggingface.co/datasets/{POLAR_DATASET}/resolve/main/rollouts"
POLAR_DIR = BASE_DIR / "polar_rollouts"
POLAR_RATE_LIMIT = 0.5  # seconds between HF API calls


def get_hf_token() -> str:
    """Read HuggingFace token from secrets."""
    try:
        with open("/root/.secrets/api_keys.env") as f:
            for line in f:
                if line.startswith("HF_TOKEN="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return os.environ.get("HF_TOKEN", "")


def _fetch_polar_dir_listing(subdir: str = "") -> list:
    """List files/dirs in POLAR dataset via HF API."""
    url = POLAR_API_BASE if not subdir else f"{POLAR_API_BASE}/{subdir}"
    headers = {"User-Agent": "SN66-Collector/2.0"}
    token = get_hf_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logging.warning(f"[S7] Failed to list POLAR dir '{subdir}': {e}")
        return []


def _download_polar_rollout(file_path: str) -> list:
    """Download and decompress a single .jsonl.gz rollout file from HF."""
    url = f"https://huggingface.co/datasets/{POLAR_DATASET}/resolve/main/{file_path}"
    headers = {"User-Agent": "SN66-Collector/2.0"}
    token = get_hf_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=120) as resp:
            compressed = resp.read()
        
        decompressed = gzip.decompress(compressed)
        records = []
        for line in decompressed.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
        return records
    except Exception as e:
        logging.warning(f"[S7] Failed to download {file_path}: {e}")
        return []


def build_polar_enrichment(polar_record: dict) -> dict:
    """Extract training-relevant fields from a POLAR rollout record."""
    return {
        "task_name":     polar_record.get("task_name", ""),
        "rollout_id":    polar_record.get("rollout_id", ""),
        "role":          polar_record.get("role", ""),  # king or challenger
        "issue":         polar_record.get("issue", ""),
        "final_patch":   polar_record.get("final_patch", ""),
        "success":       polar_record.get("success", False),
        "exit_reason":   polar_record.get("exit_reason", ""),
        "steps":         polar_record.get("steps", 0),
        "cost":          polar_record.get("cost", 0.0),
        "repo":          polar_record.get("repo", ""),
        "agent_hash":    polar_record.get("agent_hash", ""),
        "commit_sha":    polar_record.get("commit_sha", ""),
        "started_at":    polar_record.get("started_at", ""),
        "finished_at":   polar_record.get("finished_at", ""),
        "miner_logs":    polar_record.get("miner_logs", "")[:5000],  # truncate huge logs
    }


def run_source7_polar_rollouts(state: dict, dry_run: bool = False) -> int:
    """Source 7: Download POLAR rollouts from HuggingFace and store as enrichment data.
    
    Indexes by task_name for cross-referencing with Source 1 SFT/DPO records.
    Tracks processed directories to avoid re-downloading.
    """
    try:
        POLAR_DIR.mkdir(parents=True, exist_ok=True)
        
        # Track which directories we've already processed
        processed_dirs = set(state.get("polar_processed_dirs", []))
        polar_index_path = POLAR_DIR / "polar_index.jsonl"
        existing_ids = load_jsonl_ids(polar_index_path, id_field="rollout_id")
        
        now_utc = datetime.now(timezone.utc).isoformat()
        total_new = 0
        
        # List all rollout directories
        dir_listing = _fetch_polar_dir_listing()
        rollout_dirs = [
            item["path"].replace("rollouts/", "")
            for item in dir_listing
            if item.get("type") == "directory"
        ]
        
        if not rollout_dirs:
            logging.info("[S7] No POLAR rollout directories found")
            return 0
        
        for dir_name in sorted(rollout_dirs):
            if dir_name in processed_dirs:
                continue
            
            logging.info(f"[S7] Processing POLAR directory: {dir_name}")
            time.sleep(POLAR_RATE_LIMIT)
            
            # List files in this directory
            files = _fetch_polar_dir_listing(dir_name)
            jsonl_files = [
                f["path"]
                for f in files
                if f["path"].endswith(".jsonl.gz")
            ]
            
            dir_new = 0
            for file_path in jsonl_files:
                time.sleep(POLAR_RATE_LIMIT)
                records = _download_polar_rollout(file_path)
                
                for rec in records:
                    rollout_id = rec.get("rollout_id", "")
                    if not rollout_id or rollout_id in existing_ids:
                        continue
                    
                    enrichment = build_polar_enrichment(rec)
                    enrichment["collected_at"] = now_utc
                    enrichment["polar_file"] = file_path
                    
                    if not dry_run:
                        append_jsonl(polar_index_path, enrichment)
                        existing_ids.add(rollout_id)
                    
                    dir_new += 1
                
                if dir_new % 50 == 0 and dir_new > 0:
                    logging.info(f"[S7]   ... {dir_new} rollouts from {dir_name}")
            
            if not dry_run:
                processed_dirs.add(dir_name)
                state["polar_processed_dirs"] = sorted(processed_dirs)
            
            total_new += dir_new
            logging.info(f"[S7] Directory {dir_name}: +{dir_new} rollouts")
        
        if total_new > 0:
            state["polar_rollouts_collected"] = state.get("polar_rollouts_collected", 0) + total_new
            logging.info(f"[S7] +{total_new} POLAR rollouts "
                         f"(total: {state.get('polar_rollouts_collected', 0)})")
        
        return total_new
    except Exception as e:
        logging.error(f"[S7] Error: {e}", exc_info=True)
        return 0
```

### Where to add in the main loop:

In the `run_all_sources()` function (or equivalent main loop), add after Source 6:

```python
# Source 7: POLAR rollouts (new — task patches + issue descriptions)
if cycle_count % 12 == 7:  # Every ~60 minutes (assuming 5-min cycles)
    n = run_source7_polar_rollouts(state, dry_run=False)
    if n > 0:
        logging.info(f"[S7] Collected {n} new POLAR rollouts")
```

### State additions needed:

Add to `DEFAULT_STATE` dict:
```python
"polar_processed_dirs":    [],
"polar_rollouts_collected": 0,
```

---

## 4. Backfill Script: Enrich Existing SFT/DPO with POLAR Data

This script cross-references existing records with POLAR data to fix `instruction` and `output` fields:

```python
#!/usr/bin/env python3
"""backfill_polar_enrichment.py — Enrich existing SFT/DPO records with POLAR task data.

Usage:
    python3 backfill_polar_enrichment.py [--dry-run]

Reads:
  - /home/t68/sn66-training/data/live/polar_rollouts/polar_index.jsonl
  - /home/t68/sn66-training/data/live/sft/*.jsonl
  - /home/t68/sn66-training/data/live/dpo/*.jsonl

Writes:
  - /home/t68/sn66-training/data/live/sft_enriched/*.jsonl
  - /home/t68/sn66-training/data/live/dpo_enriched/*.jsonl
"""

import json
import sys
import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

# Configurable base - set to T68-S1 paths
BASE_DIR = Path("/home/t68/sn66-training/data/live")
# Override for Hetzner1:
# BASE_DIR = Path("/root/sn66-ninja/training_data/live")

POLAR_INDEX = BASE_DIR / "polar_rollouts" / "polar_index.jsonl"
SFT_DIR = BASE_DIR / "sft"
DPO_DIR = BASE_DIR / "dpo"
SFT_ENRICHED_DIR = BASE_DIR / "sft_enriched"
DPO_ENRICHED_DIR = BASE_DIR / "dpo_enriched"

DRY_RUN = "--dry-run" in sys.argv


def load_polar_index() -> dict:
    """Load POLAR index, keyed by task_name.
    Returns dict: task_name -> {role -> polar_record}
    Multiple rollouts per task (king + challenger) are possible.
    """
    index = defaultdict(dict)  # task_name -> {role -> record}
    if not POLAR_INDEX.exists():
        print(f"ERROR: POLAR index not found at {POLAR_INDEX}")
        print("Run the collector with Source 7 first to populate it.")
        sys.exit(1)
    
    count = 0
    with open(POLAR_INDEX) as f:
        for line in f:
            rec = json.loads(line.strip())
            tn = rec.get("task_name", "")
            role = rec.get("role", "unknown")
            if tn:
                index[tn][role] = rec
                count += 1
    
    print(f"Loaded {count} POLAR rollouts for {len(index)} unique tasks")
    return dict(index)


def enrich_sft_record(rec: dict, polar_index: dict) -> dict:
    """Enrich an SFT record with POLAR data."""
    task_name = rec.get("task_name", "")
    if task_name not in polar_index:
        return rec  # No POLAR data available
    
    polar_data = polar_index[task_name]
    winner = rec.get("winner", "")
    
    # Get the winner's rollout (king or challenger)
    polar_rec = polar_data.get(winner, {})
    if not polar_rec:
        # Fallback: try any available role
        polar_rec = next(iter(polar_data.values()), {})
    
    enriched = dict(rec)
    
    # Fix instruction: use POLAR issue text instead of bare task_name
    issue = polar_rec.get("issue", "")
    if issue:
        enriched["instruction"] = issue
        enriched["instruction_source"] = "polar_issue"
    
    # Fix output: use POLAR final_patch instead of agent.py diff
    final_patch = polar_rec.get("final_patch", "")
    if final_patch:
        enriched["output"] = final_patch
        enriched["output_source"] = "polar_final_patch"
    
    # Add enrichment metadata
    enriched["polar_rollout_id"] = polar_rec.get("rollout_id", "")
    enriched["polar_success"] = polar_rec.get("success", None)
    enriched["polar_steps"] = polar_rec.get("steps", None)
    enriched["polar_exit_reason"] = polar_rec.get("exit_reason", "")
    enriched["polar_repo"] = polar_rec.get("repo", "")
    enriched["enriched_at"] = datetime.now(timezone.utc).isoformat()
    
    return enriched


def enrich_dpo_record(rec: dict, polar_index: dict) -> dict:
    """Enrich a DPO record with POLAR data."""
    task_name = rec.get("task_name", "")
    if task_name not in polar_index:
        return rec
    
    polar_data = polar_index[task_name]
    enriched = dict(rec)
    
    # Get king and challenger rollouts
    king_polar = polar_data.get("king", {})
    challenger_polar = polar_data.get("challenger", {})
    
    winner = rec.get("winner", "")
    if winner == "king":
        chosen_polar = king_polar
        rejected_polar = challenger_polar
    else:
        chosen_polar = challenger_polar
        rejected_polar = king_polar
    
    # Fix instruction (add issue text)
    issue = king_polar.get("issue", "") or challenger_polar.get("issue", "")
    if issue:
        enriched["instruction"] = issue
        enriched["instruction_source"] = "polar_issue"
    
    # Fix chosen/rejected patches
    if chosen_polar.get("final_patch"):
        enriched["chosen_patch"] = chosen_polar["final_patch"]
        enriched["chosen_patch_source"] = "polar_final_patch"
    if rejected_polar.get("final_patch"):
        enriched["rejected_patch"] = rejected_polar["final_patch"]
        enriched["rejected_patch_source"] = "polar_final_patch"
    
    # Enrichment metadata
    enriched["polar_chosen_rollout_id"] = chosen_polar.get("rollout_id", "")
    enriched["polar_rejected_rollout_id"] = rejected_polar.get("rollout_id", "")
    enriched["polar_chosen_success"] = chosen_polar.get("success", None)
    enriched["polar_rejected_success"] = rejected_polar.get("success", None)
    enriched["enriched_at"] = datetime.now(timezone.utc).isoformat()
    
    return enriched


def process_jsonl_dir(input_dir: Path, output_dir: Path, enrich_fn, polar_index: dict, label: str):
    """Process all .jsonl files in input_dir, write enriched versions to output_dir."""
    if not input_dir.exists():
        print(f"  {label}: input dir {input_dir} not found, skipping")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for jsonl_file in sorted(input_dir.glob("*.jsonl")):
        output_file = output_dir / jsonl_file.name
        total = 0
        enriched_count = 0
        
        with open(jsonl_file) as inf:
            lines = inf.readlines()
        
        enriched_lines = []
        for line in lines:
            rec = json.loads(line.strip())
            total += 1
            enriched = enrich_fn(rec, polar_index)
            if enriched.get("enriched_at"):
                enriched_count += 1
            enriched_lines.append(json.dumps(enriched, ensure_ascii=False))
        
        if not DRY_RUN:
            with open(output_file, "w") as outf:
                for eline in enriched_lines:
                    outf.write(eline + "\n")
        
        pct = (enriched_count / total * 100) if total > 0 else 0
        print(f"  {label} {jsonl_file.name}: {enriched_count}/{total} enriched ({pct:.1f}%)")


def main():
    print(f"=== POLAR Backfill Enrichment {'(DRY RUN)' if DRY_RUN else ''} ===")
    print(f"Base dir: {BASE_DIR}")
    print()
    
    polar_index = load_polar_index()
    
    print("\n--- Enriching SFT records ---")
    process_jsonl_dir(SFT_DIR, SFT_ENRICHED_DIR, enrich_sft_record, polar_index, "SFT")
    
    print("\n--- Enriching DPO records ---")
    process_jsonl_dir(DPO_DIR, DPO_ENRICHED_DIR, enrich_dpo_record, polar_index, "DPO")
    
    print("\nDone!")


if __name__ == "__main__":
    main()
```

---

## 5. Collector Restart SOP for T68-S1

### Step 1: Sync the latest collector script to T68-S1
The T68-S1 is running an OLDER version (`sn66_final_unified_collector.py`). Must update to `sn66_live_collector_v2.py` with Source 7 added.

```bash
# On Hetzner1: copy updated v2 script to T68-S1
scp /root/sn66-ninja/scripts/sn66_live_collector_v2.py \
    t68@t68-s1:/home/t68/sn66-training/scripts/sn66_live_collector_v2.py
```

### Step 2: Fix paths in the script for T68-S1
Before deploying, update these paths in the script copy for T68-S1:
```python
# OLD (Hetzner1 paths):
BASE_DIR = Path("/root/sn66-ninja/training_data/live")
SN66_DIR = Path("/home/t68/sn66-ninja")

# NEW (T68-S1 paths):
BASE_DIR = Path("/home/t68/sn66-training/data/live")
SN66_DIR = Path("/home/t68/sn66-ninja")  # This one is correct for T68-S1
```

### Step 3: Restart PM2 with the new script
```bash
ssh t68-s1 << 'EOF'
cd /home/t68/sn66-training
pm2 stop sn66-unified-collector
pm2 delete sn66-unified-collector
pm2 start scripts/sn66_live_collector_v2.py \
    --name sn66-unified-collector \
    --interpreter python3 \
    --no-autorestart
pm2 save
pm2 logs sn66-unified-collector --lines 20 --nostream
EOF
```

### Step 4: Verify it's processing new duels
```bash
ssh t68-s1 "sleep 60 && pm2 logs sn66-unified-collector --lines 10 --nostream"
# Look for: [S1] Found N new duels, [S7] Collected N POLAR rollouts
```

### Step 5: Run backfill enrichment
```bash
ssh t68-s1 << 'EOF'
cd /home/t68/sn66-training
# Wait for Source 7 to populate POLAR index (check every 5 min)
while [ ! -f data/live/polar_rollouts/polar_index.jsonl ]; do
    echo "Waiting for POLAR index..."
    sleep 300
done
python3 scripts/backfill_polar_enrichment.py
EOF
```

---

## 6. Summary of All Required Code Changes

### Change 1 (CRITICAL): Add Source 7 to collector
- Add `run_source7_polar_rollouts()` function (see Section 3 above)
- Add to main loop every ~60 minutes
- Add `polar_processed_dirs` and `polar_rollouts_collected` to state

### Change 2 (CRITICAL): Fix SFT instruction/output in collector
In `build_sft_record()`, after building the base record, add POLAR enrichment:
```python
# After building base SFT record, try POLAR enrichment
polar_rec = _get_polar_for_task(task_ctx["task_name"], winner_label)
if polar_rec:
    record["instruction"] = polar_rec.get("issue", record["instruction"])
    record["output"] = polar_rec.get("final_patch", record["output"])
    record["output_source"] = "polar"
```

### Change 3 (CRITICAL): Fix DPO chosen/rejected patches
Same pattern for `build_dpo_record()` — use POLAR `final_patch` for chosen/rejected instead of `_get_best_patch()` which returns agent.py diffs.

### Change 4 (MODERATE): In-memory POLAR cache for real-time enrichment
Add a module-level dict that caches POLAR data by task_name so Source 1 can use it during record building without disk I/O:
```python
_POLAR_TASK_CACHE: dict = {}  # task_name -> {role -> polar_record}

def _load_polar_cache():
    """Load POLAR index into memory for fast lookup during Source 1 processing."""
    global _POLAR_TASK_CACHE
    polar_path = POLAR_DIR / "polar_index.jsonl"
    if not polar_path.exists():
        return
    _POLAR_TASK_CACHE.clear()
    with open(polar_path) as f:
        for line in f:
            rec = json.loads(line.strip())
            tn = rec.get("task_name", "")
            role = rec.get("role", "unknown")
            if tn:
                if tn not in _POLAR_TASK_CACHE:
                    _POLAR_TASK_CACHE[tn] = {}
                _POLAR_TASK_CACHE[tn][role] = rec

def _get_polar_for_task(task_name: str, role: str = "") -> Optional[dict]:
    """Get POLAR data for a task. Returns best matching rollout."""
    if task_name not in _POLAR_TASK_CACHE:
        return None
    task_data = _POLAR_TASK_CACHE[task_name]
    if role and role in task_data:
        return task_data[role]
    return next(iter(task_data.values()), None)
```

### Change 5 (LOW): Fix Hetzner1 SN66_DIR path
Only needed if Hetzner1 collector is restarted:
```python
SN66_DIR = Path("/root/sn66-ninja")  # Not /home/t68/sn66-ninja
```

---

## 7. Priority Order

1. **Add Source 7 to T68-S1 collector** → starts collecting POLAR data immediately
2. **Run backfill enrichment** → fixes all existing records that have POLAR matches
3. **Fix real-time enrichment** → new records get POLAR data at collection time
4. **Consolidate scripts** → unify Hetzner1/T68-S1 into one script with env-based paths
5. **Monitor POLAR dataset growth** → as more historical data appears, re-run backfill

---

## 8. Data Quality Impact Assessment

**Current state (before fix):**
| Field | Quality | Issue |
|-------|---------|-------|
| SFT instruction | ❌ BROKEN | Bare task name string, no problem description |
| SFT output | ❌ BROKEN | agent.py diffs (53%) or empty (47%), never task patches |
| DPO chosen_patch | ❌ BROKEN | agent.py diffs or empty, not task solutions |
| DPO rejected_patch | ❌ BROKEN | Same issue |
| judge_rationale | ✅ OK | Real judge reasoning about task quality |
| task_summary | ⚠️ PARTIAL | Truncated rationale (500 chars) or empty |

**After POLAR fix:**
| Field | Quality | Source |
|-------|---------|--------|
| SFT instruction | ✅ FIXED | POLAR `issue` (938-2199 chars of real task description) |
| SFT output | ✅ FIXED | POLAR `final_patch` (6730-26385 chars of real task solution) |
| DPO chosen_patch | ✅ FIXED | POLAR `final_patch` for winning role |
| DPO rejected_patch | ✅ FIXED | POLAR `final_patch` for losing role |
| judge_rationale | ✅ OK | Unchanged |
| task_summary | ✅ ENHANCED | POLAR `issue` text available |

**Coverage caveat:** POLAR currently only has data from 2026-05-27 onwards. Historical records (duels 5004-5707) cannot be enriched until POLAR adds historical data. New records collected going forward will have full enrichment.

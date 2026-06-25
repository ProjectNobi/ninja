# POLAR Dataset Analysis & T68 Training Data Optimization
**Date:** 2026-05-27 | **Author:** T68Bot Opus Subagent

---

## 1. POLAR Dataset Schema & Sample Trajectory

### 1.1 What is POLAR?

**Paper:** [arXiv:2605.24220](https://arxiv.org/abs/2605.24220) — "Agentic RL on Any Harness at Scale"
**Authors:** NVIDIA Research (Binfeng Xu, Hao Zhang, et al.)
**Key insight:** POLAR treats the agent harness as a black box, proxies LLM API calls, records token-level interactions, and reconstructs token-faithful trajectories for RL training.

Applied to SN66 by unarbos: records FULL solver trajectories from retired duels, publishing them to HuggingFace.

### 1.2 Dataset Location

- **HF Repo:** `Wejh/ninja-rollouts-polar`
- **Latest batch:** `rollouts/2026-05-27-17/` — 112MB across ~33 `.jsonl.gz` files
- **Naming:** `validate-{timestamp}-{task_id}.jsonl.gz` — one file per retired task
- **Each file:** 1 JSONL record per participant (king + challenger = 2 records per duel task)
- **Commit:** `cb8d998` — "Publish retired tau rollouts for validate-20260527171836-065761"

### 1.3 Full Schema (schema_version: 1)

| Field | Type | Description |
|-------|------|-------------|
| `agent_hash` | str (64 chars) | SHA256 of agent.py |
| `agent_source` | dict | `{agent_file, commit_sha, kind, local_path, raw}` — exact agent provenance |
| `commit_sha` | str (40 chars) | Commit SHA of the agent's code |
| `cost` | float | LLM API cost in USD (e.g., $0.0237) |
| `exit_reason` | str | `completed` / `time_limit_exceeded` / `solver_error` |
| `final_patch` | str | **FULL unified diff** of the agent's solution (avg 29K chars) |
| `finished_at` | str | ISO timestamp when run finished |
| `issue` | str (~1163 chars) | **Full task description/issue text** |
| `miner_logs` | str (~16K chars) | **Complete step-by-step log**: MODEL_RESPONSE, OBSERVATION, commands, outputs |
| `repo` | str | Git repo name for the task |
| `role` | str | `king` or challenger name |
| `rollout_id` | str | Unique rollout ID (e.g., `rol_de1eb6c4d3527a6fa4e0e99b`) |
| `runner` | dict | `{backend, container_network, image, timeout_seconds}` |
| `schema_version` | int | Always 1 |
| `solution_name` | str | `king` or challenger identifier |
| `started_at` | str | ISO timestamp when run started |
| `steps` | int | Number of LLM conversation turns (e.g., 14, 31) |
| `success` | bool | Whether the solve completed successfully |
| `task_name` | str | Task identifier (matches duel round task names) |
| `trajectory` | list | **FULL trajectory** — see 1.4 below |
| `visibility` | str | `public_after_task_retired` |

### 1.4 Trajectory Structure (THE GOLD MINE)

Each trajectory is a list of events (100-800+ events per run). Three event types:

#### Event Type: `command` (source: `tau_runner_process_hook`)
```json
{
  "type": "command",
  "cmd": "grep -r 'localhost:8080' --files-with-matches .",
  "cwd": "/work/repo",
  "exit_code": 0,
  "duration_ms": 14,
  "stdout": "./components/weekly-salary-screen.tsx\n...",
  "stderr": "",
  "timed_out": false,
  "started_at": "...",
  "finished_at": "..."
}
```

#### Event Type: `llm_call` (source: `tau_proxy`)
```json
{
  "type": "llm_call",
  "model_requested": "minimax/minimax-m2.7",
  "model_effective": "minimax/minimax-m2.7-20260318",
  "request": {"messages": [...], "max_tokens": 8192, ...},
  "response": {"choices": [...], "usage": {...}},
  "usage": {"prompt_tokens": 37350, "completion_tokens": 712, "reasoning_tokens": 226},
  "cost": 0.01128,
  "latency_ms": 5027,
  "status_code": 200
}
```

#### Event Type: `edit` (source: `tau_runner_process_hook`)
```json
{
  "type": "edit",
  "diff": "diff --git a/file.py b/file.py\n...",
  "repo_diff_sha256": "..."
}
```

### 1.5 miner_logs — Structured Step Log

The `miner_logs` field contains a human-readable step-by-step log:
```
===== STEP 1 =====
MODEL_RESPONSE:
<plan>
- Requirement: Replace all occurrences of `http://localhost:8080`...
</plan>
<command>
rg -F 'localhost:8080' --files-with-matches
</command>

OBSERVATION 1/1:
COMMAND: rg -F 'localhost:8080' --files-with-matches
EXIT_CODE: 127
STDERR: /bin/bash: line 1: rg: command not found

===== STEP 2 =====
MODEL_RESPONSE:
<command>
grep -r 'localhost:8080' --files-with-matches .
</command>
...
```

### 1.6 Sample Record Stats

| Metric | King (simple task) | King (complex task) |
|--------|-------------------|-------------------|
| Steps | 14 | 31 |
| Trajectory events | 201 | 796 |
| LLM calls | 14 | 31 |
| Command events | 186 | ~760 |
| Edit events | 1 | ~5 |
| Cost | $0.024 | $0.159 |
| Final patch | 29,564 chars | 32,218 chars |
| Duration | ~80s | ~7min |

---

## 2. POLAR → SFT/DPO Conversion Strategy

### 2.1 SFT Conversion (Trajectory → Training Pairs)

**Strategy A: Full trajectory as training signal**
```json
{
  "instruction": "<issue text from 'issue' field>",
  "input": "<task_name + repo context>",
  "output": "<final_patch>",
  "trajectory_steps": <steps>,
  "trajectory_cost": <cost>,
  "success": true,
  "source": "polar_rollout",
  "model_used": "<model_effective from llm_call events>",
  "quality_label": "king_completed"
}
```

**Strategy B: Step-by-step SFT (richer signal)**
For each LLM call event, extract:
- System + user messages → `instruction`
- Assistant response → `output`
- Tool/command results from following command events → `context`

This gives ~14-31 SFT pairs per rollout, each teaching one reasoning step.

**Strategy C: miner_logs parsed SFT**
Parse the structured `miner_logs` into STEP→OBSERVATION pairs:
- `MODEL_RESPONSE` → `output`
- `OBSERVATION` (command output) → `context for next turn`

### 2.2 DPO Conversion (King vs Challenger)

Each task file contains records for both king AND challenger. Pair them:
```json
{
  "instruction": "<issue text>",
  "chosen": "<king's final_patch>",        // if king won
  "rejected": "<challenger's final_patch>", // if challenger lost
  "chosen_steps": <king_steps>,
  "rejected_steps": <challenger_steps>,
  "chosen_cost": <king_cost>,
  "rejected_cost": <challenger_cost>,
  "task_name": "<task_name>",
  "source": "polar_rollout_dpo"
}
```

**Win determination:** Cross-reference with `ninja66.ai/duels/{id}.json` for judge scores, or use `success` field + step count as proxy.

### 2.3 Unique POLAR Advantages Over Current Data

| Signal | Current Collector | POLAR |
|--------|------------------|-------|
| Final patch | ✅ (via commit diff) | ✅ (direct in record) |
| Task description | ❌ (only task_name) | ✅ (full `issue` text) |
| Step-by-step reasoning | ❌ | ✅ (miner_logs + trajectory) |
| Tool usage patterns | ❌ | ✅ (command events with stdout/stderr) |
| Error recovery | ❌ | ✅ (failed commands → retries visible) |
| LLM call details | ❌ | ✅ (full messages, tokens, cost) |
| Model identity | ❌ | ✅ (model_effective per call) |
| Duration per step | ❌ | ✅ (duration_ms per event) |
| Agent source code | ❌ (separate king_history) | ✅ (agent_source.commit_sha) |
| Edit diffs mid-run | ❌ | ✅ (edit events with diff) |

### 2.4 Example Conversion

**POLAR record → SFT pair:**
```json
{
  "id": "polar_sft_validate-20260527170009-065830_king",
  "source": "polar_rollout",
  "task_name": "validate-20260527170009-065830",
  "issue_text": "Replace all occurrences of http://localhost:8080 with http://13.206.112.19:8080...",
  "instruction": "You are a coding agent. Fix this issue:\n<issue>\nReplace all occurrences of http://localhost:8080...\n</issue>\n\nRepo: <repo_name>\n",
  "output": "diff --git a/app/api/auth/login/route.ts ...",
  "steps": 14,
  "exit_reason": "completed",
  "success": true,
  "cost_usd": 0.0237,
  "agent_model": "minimax/minimax-m2.7-20260318",
  "role": "king"
}
```

---

## 3. Collector Audit Findings

### 3.1 Script Overview

- **File:** `/root/sn66-ninja/scripts/sn66_live_collector_v2.py` (on Hetzner1)
- **Also running on T68-S1** as PM2 `sn66-unified-collector`
- **Lines:** ~1,200+ (comprehensive, well-documented)
- **Sources:** 6 data sources (S1-S6)

### 3.2 Current Sources

| Source | What | Status | Records |
|--------|------|--------|---------|
| S1: Live duels | SFT/DPO from ninja66.ai duels | ✅ Running | 14,360 SFT, 12,352 DPO |
| S2: King history | agent.py at each king commit | ✅ Complete | 34 kings |
| S3: PR outcomes | Merged/rejected PRs with diffs | ✅ Complete | 1,598 PRs |
| S4: Judge feedback | DPO losses → lesson pairs | ✅ Complete | 2,506 records |
| S5: Miner history | Our agent_*.py versions | ⚠️ 0 records | miner_files_seen=[] |
| S6: Repo context | Pre-PR file context enrichment | ✅ Running | File exists but empty dir |

### 3.3 Critical Findings

#### BUG-1: Source 5 (Miner History) collecting 0 records
- **Cause:** `SN66_DIR = Path("/home/t68/sn66-ninja")` (line ~60) but the agent files are at `/root/sn66-ninja/` on Hetzner1 and `/home/t68/sn66-ninja/` on T68-S1
- On Hetzner1: `BASE_DIR = Path("/root/sn66-ninja/training_data/live")` but `SN66_DIR` points to `/home/t68/sn66-ninja` which doesn't exist
- On T68-S1: `SN66_DIR` is correct (`/home/t68/sn66-ninja`) but `scan_agent_files()` looks for patterns like `agent_t68_v*.py` — need to verify these exist
- **Impact:** No miner version tracking. `miner_files_seen: []`, `miner_versions_collected: 0`
- **Fix:** Ensure SN66_DIR matches the actual location on whichever server runs the collector

#### BUG-2: Collector running on BOTH Hetzner1 and T68-S1 simultaneously
- Hetzner1: `state.json` shows `last_processed_duel_id: 5557` with data at `/root/sn66-ninja/training_data/live/`
- T68-S1: PM2 `sn66-unified-collector` is online, data at `/home/t68/sn66-ninja/training_data/live/`
- **Both directories have separate state.json files** — they're collecting independently
- **Risk:** Duplicate API calls, double GitHub rate limit consumption, potential data drift
- **Recommendation:** Run on ONE server only (T68-S1 preferred — closer to training)

#### BUG-3: Collector STOPPED on Hetzner1
- `last_run_utc: "2026-05-25T12:18:50"` — hasn't run in 2+ days
- No PM2 process visible on Hetzner1 for the collector
- T68-S1 collector `state.json` is tiny (929 bytes) with likely different cursor position
- **Impact:** Missing ~2 days of duels

#### GAP-1: No POLAR/HuggingFace rollout data integration
- The collector has no Source 6+ for downloading POLAR rollout data
- This is the biggest missing data source — trajectory data is far richer than what S1-S5 collect
- **See Section 5 for recommended implementation**

#### GAP-2: SFT output field is agent.py diff, not task-specific patch
- Looking at SFT sample records: `"output": "diff --git a/agent.py b/agent.py\nindex 65e51f61..25926390 100644\n--- a/agent.py\n+++ b/agent.py\n@@ -55,8 +55,6 @@\n..."` 
- **This is the AGENT CODE diff, not the task patch!** The `winner_patch` from `_get_best_patch()` fetches the commit that promoted the agent to king — which is the agent.py diff
- For king (private_published source): commit `f2cc71310a96cdb...` at `unarbos/ninja` = the king's agent.py code
- For challengers (private source): commit SHA points to private-submission repo → empty string
- **This means:** Most SFT `output` and DPO `chosen_patch`/`rejected_patch` fields contain the AGENT'S CODE, not the actual task solution
- **Critical quality issue** — the training data associates task descriptions with agent source code, not with the patches the agent produced for those tasks
- **POLAR rollouts fix this** — `final_patch` is the actual task solution

#### GAP-3: Missing task description in SFT records
- `"instruction": "validate-20260509030249-064687"` — just the task name, not the actual problem description
- `"task_summary"` has partial judge rationale but not the original issue/task text
- POLAR rollouts have the full `issue` text

### 3.4 Positive Findings

- **Idempotency:** All sources use ID-based dedup (load_jsonl_ids) — safe against duplicate writes
- **Atomic writes:** File-locked JSONL appends, temp-file atomic overwrites
- **Counter sync:** FIX-L3 recounts actual records on startup to fix drift
- **Rate limiting:** Proper 1 req/s GitHub API rate limiting, 429 backoff
- **Health monitoring:** FIX-L2 detects 3+ consecutive anomalous duels, sends Telegram alert
- **King change detection:** NEW-1 checks for king promotion on startup
- **Task type classification:** UPGRADE-1 classifies BUGFIX/FEATURE/UPDATE/API
- **Edit quality labeling:** UPGRADE-2 labels excellent/good/over_edit/under_edit/empty
- **Repo context enrichment:** UPGRADE-3 (S6) fetches pre-PR file context

---

## 4. Data Quality Assessment

### 4.1 SFT Records (14,360 total)

**Sample analysis of 3 records from duel 5004:**

| Field | Record 1 | Record 2 | Record 3 |
|-------|----------|----------|----------|
| task_type | API | API | BUGFIX |
| winner | king | king | challenger |
| judge_score | (king won) | (king won) | 0.96 |
| loser_score | | | 0.84 |
| winner_patch | ✅ Has diff (agent.py) | ✅ Has diff (agent.py) | ❌ Empty (private) |
| instruction | task_name only | task_name only | task_name only |
| task_summary | ✅ Judge rationale | ✅ Judge rationale | ✅ Judge rationale |

**Quality Issues:**
1. **🔴 CRITICAL: `output` field = agent.py diff, NOT task solution** — training on this teaches the model to produce agent code, not patches
2. **🟡 `instruction` = task_name** — no actual problem description, model can't learn task→patch mapping
3. **🟡 ~50% of patches are empty** for private-submission challengers — these SFT records have no output
4. **🟢 `task_summary`** from judge rationale provides useful quality signal
5. **🟢 `task_type` classification** adds useful metadata

### 4.2 DPO Records (12,352 total)

| Field | Record 1 | Record 2 |
|-------|----------|----------|
| score_diff | 0.30 | 0.36 |
| chosen_patch | ✅ agent.py diff | ✅ agent.py diff |
| rejected_patch | ❌ Empty (private) | ✅ agent.py diff |
| edit_quality | not_available | good |
| chosen_lines | >100 | >100 |

**Quality Issues:**
1. **🔴 CRITICAL: Same agent.py diff problem** — chosen/rejected patches are agent code diffs
2. **🟡 Many `not_available` edit_quality** when both patches can't be fetched
3. **🟢 Score diff threshold (0.15) filters marginal cases**
4. **🟢 Judge rationale provides clear preference signal**

### 4.3 Judge Feedback (2,506 total)

| Field | Sample |
|-------|--------|
| instruction | ✅ Full judge rationale (post FIX-G1 backfill) |
| winning_patch | agent.py diff |
| losing_patch | Empty (private) |
| lesson | Pattern-extracted lesson text |

**Quality Issues:**
1. **🔴 Same patch content problem** — winning/losing patches are agent diffs
2. **🟢 `instruction` field now correctly populated** (NEW-2 backfill complete)
3. **🟢 Synthesized lessons** provide valuable meta-reasoning signal

---

## 5. Prioritized Action List

### Priority 1 (CRITICAL — Do Immediately): Add POLAR Rollout Downloader

**Why:** POLAR data fixes ALL critical quality issues (real task solutions, full issue text, step-by-step trajectories) and provides 10x richer training signal.

**Implementation plan:**
1. Add Source 7 to collector: `run_source7_polar_rollouts()`
2. Poll HuggingFace API: `https://huggingface.co/api/datasets/Wejh/ninja-rollouts-polar/tree/main/rollouts/`
3. Download new `.jsonl.gz` files from each batch
4. Parse records → convert to:
   - **SFT:** `issue` → `instruction`, `final_patch` → `output` (the REAL task patch)
   - **DPO:** pair king vs challenger by `task_name`, use `success` + `steps` + `cost` as preference signal
   - **Trajectory SFT:** Extract miner_logs STEP→OBSERVATION pairs for step-by-step training
5. Write to new directories: `polar_sft/`, `polar_dpo/`, `polar_trajectory/`

**Expected data yield per batch:** ~33 tasks × 2 participants = ~66 rollouts → ~66 SFT + ~33 DPO pairs + ~33×20 = 660 step-level SFT pairs

### Priority 2 (HIGH — Fix This Week): Fix Existing Data Quality

1. **Stop using agent.py diffs as patch output** — the current SFT/DPO records train the model on wrong data
2. **Add `issue` text from POLAR** to existing SFT records by matching `task_name`
3. **Cross-reference POLAR `final_patch` with duel `task_name`** to get actual task solutions for historical records
4. **Fix Source 5** on the active server — ensure SN66_DIR points to correct path

### Priority 3 (MEDIUM — This Sprint): Consolidate Collectors

1. **Pick ONE server** for the collector (T68-S1 recommended)
2. **Merge data** from both Hetzner1 and T68-S1 into one unified dataset
3. **Restart the collector** — it's been stopped for 2+ days
4. **Verify data pipeline** end-to-end: collector → JSONL → training script

### Priority 4 (LOW — Nice to Have): Enhanced Training Signal

1. **Trajectory-level SFT** from POLAR miner_logs — each step teaches one reasoning move
2. **Tool usage frequency analysis** from command events — which commands win duels?
3. **Cost-aware DPO** — prefer cheaper solutions when quality is equal
4. **Agent model tracking** — know which model produced each trajectory for model-specific DPO
5. **Error recovery patterns** — extract failed_command → recovery_command pairs

---

## 6. POLAR Download Script Template

```python
#!/usr/bin/env python3
"""Source 7: POLAR rollout downloader for SN66 training pipeline."""

import gzip
import json
import urllib.request
import time
from pathlib import Path

HF_API_BASE = "https://huggingface.co/api/datasets/Wejh/ninja-rollouts-polar/tree/main/rollouts"
HF_RESOLVE = "https://huggingface.co/datasets/Wejh/ninja-rollouts-polar/resolve/main"
POLAR_SFT_DIR = Path("training_data/live/polar_sft")
POLAR_DPO_DIR = Path("training_data/live/polar_dpo")
POLAR_TRAJECTORY_DIR = Path("training_data/live/polar_trajectory")

def fetch_polar_batches():
    """List available rollout batch directories."""
    url = HF_API_BASE
    req = urllib.request.Request(url, headers={"User-Agent": "SN66-POLAR-Collector/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def download_rollout(file_path: str) -> list:
    """Download and parse a .jsonl.gz rollout file."""
    url = f"{HF_RESOLVE}/{file_path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SN66-POLAR-Collector/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    decompressed = gzip.decompress(raw)
    records = []
    for line in decompressed.decode("utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records

def convert_to_sft(record: dict) -> dict:
    """Convert POLAR rollout → SFT training record."""
    return {
        "id": f"polar_sft_{record['task_name']}_{record['role']}",
        "source": "polar_rollout",
        "task_name": record["task_name"],
        "issue_text": record.get("issue", ""),
        "instruction": record.get("issue", ""),
        "output": record.get("final_patch", ""),
        "steps": record.get("steps", 0),
        "exit_reason": record.get("exit_reason", ""),
        "success": record.get("success", False),
        "cost_usd": record.get("cost", 0),
        "role": record.get("role", ""),
        "agent_model": _extract_model(record),
        "agent_hash": record.get("agent_hash", ""),
    }

def _extract_model(record: dict) -> str:
    """Extract effective model from first llm_call in trajectory."""
    for event in (record.get("trajectory") or []):
        if isinstance(event, dict) and event.get("type") == "llm_call":
            return event.get("model_effective", "")
    return ""
```

---

## Appendix: Data Inventory

### Hetzner1 (`/root/sn66-ninja/training_data/live/`)
| File | Size | Records |
|------|------|---------|
| sft/2026-05-25.jsonl | 420MB | 14,360 |
| dpo/2026-05-25.jsonl | 355MB | 12,352 |
| judge_feedback/judge_feedback.jsonl | 71MB | 2,506 |
| pr_outcomes/pr_outcomes.jsonl | 52MB | 1,598 |
| king_history/king_history.jsonl | 6MB | 34 |
| miner_history/ | empty | 0 |
| repo_context_enrichment.jsonl | — | — |
| **Last duel processed:** 5557 | | |
| **Collector status:** STOPPED (2 days) | | |

### T68-S1 (`/home/t68/sn66-ninja/training_data/live/`)
| Component | Status |
|-----------|--------|
| PM2 `sn66-unified-collector` | ✅ ONLINE |
| state.json | 929 bytes |
| Data directories | Created, sizes unknown |

### POLAR HuggingFace Dataset
| Metric | Value |
|--------|-------|
| Latest batch | 2026-05-27-17 |
| Files in batch | ~33 `.jsonl.gz` files |
| Total batch size | ~112MB compressed |
| Records per file | 1 (one participant per file) |
| Schema version | 1 |
| Trajectory events/record | 200-800 |
| LLM calls/record | 14-31 |
| Contains | Full issue text, final_patch, step-by-step trajectory, LLM call details |

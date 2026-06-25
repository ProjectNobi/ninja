# Step 1: Source Intelligence — 2026-06-14

**Generated:** 2026-06-14 ~16:45 UTC  
**Agent:** SN66 Step 1 Source Intel Subagent  
**King SHA:** `a56ffdf52ea9f18854c1efc29a884c6e5fd01a7a`  
**King installed:** 2026-06-14T06:51:01 UTC (defended 13 duels as of report time)

---

## 1a: GitHub Commit History (key changes since May 19)

### All Commits Since May 19 (newest first)

| SHA | Date | Message |
|-----|------|---------|
| `ae2158103232` | 2026-06-14 | Reject empty proxy-normalized model replies in the harness client. Read list-shaped content parts |
| `a56ffdf52ea9` | **2026-06-14** | **update tool calling regex** ← CURRENT KING |
| `3b576759a0d8` | 2026-06-11 | Merge PR #1600: Replace single-file king with multi-file agent base |
| `5c3a8f7a8206` | 2026-06-11 | Replace single-file king with multi-file agent base |
| `b79ece02c0ae` | 2026-06-07 | Promote private miner 5CV3sHpCuEmF |
| `d1b9d64f64b7` | 2026-06-07 | Promote private miner 5FCMfPxzYuL2 |
| `f935830bbe8a` | 2026-06-06 | Promote private miner 5Eo4nvNVDetk |
| `89ce953e1c8c` | 2026-06-06 | Promote private miner 5GCP3KnawxxB |
| *(5 more king promotions, 2026-06-02 to 06-05)* | | |

### Key Changes vs Last Pipeline (May 19)

**CRITICAL ARCHITECTURAL CHANGE: Multi-File Base (June 11, PR #1600)**
- `agent.py` went from **20,801 lines → 76 lines** (thin solve() wrapper)
- New multi-file structure: `agent.py` + `agent/` directory with 5 modules
- New file: `tau_agent_files.json` (lists bundle files)
- New script: `scripts/check_agent_contract.py` (pre-submission validation)
- `scripts/submit_private_submission.py` substantially updated (+103/-19 lines)

**KING-SHA SPECIFIC CHANGE: Tool Calling Regex (June 14, `a56ffdf5`)**
- Modified `agent/agent_loop.py` (+32/-2 lines)
- Added native tool-call format parsing: `_NATIVE_TOOL_CALL_RE`
- Now handles models emitting `<|tool_call_begin|>...<|tool_call_end|>` tokens natively
- Supports Kimi/Moonshot model native format in addition to bash blocks
- This is the change that created the current king (was beating previous private king)

**HARNESS CLIENT FIX: Empty Model Replies (June 14, `ae2158103232`)**
- Modified `agent/model.py` (+5/-1 lines)
- Rejects empty proxy-normalized model replies
- Reads list-shaped content parts from `text` or `content` fields
- **This commit is NEWER than the king** — the king does not yet include this fix
- Our harness should incorporate this fix

**King Promotion Velocity:** 8+ private miners promoted since May 19 (roughly 1-2/day in early June). Competition is extremely active.

---

## 1b: King Analysis (new multi-file king)

### SYSTEM_PROMPT (verbatim from `agent/prompts.py`)

```
You are a precise software engineering agent that interacts with a computer
through bash commands to fix issues in a repository checked out at the
current working directory.

Response format, every single turn:
1. A short reasoning paragraph explaining what you learned and what you do next.
2. Exactly ONE bash code block with exactly ONE command to execute, like:

```bash
nl -ba path/to/file.py | sed -n '1,80p'
```

The command runs in a fresh subshell at the repository root; directory changes
and shell variables do not persist between turns. Chain with `&&` when needed.
Never output more than one code block.
```

**Note:** This is a **minimal, clean system prompt** — no framing as "elite agent", no fancy persona, no explicit SWE methodology instructions. Just the bare contract.

### TASK_TEMPLATE (from `agent/prompts.py`) — Key Sections

The task template tells the model:
1. Solve the issue with the reference solution as judge context
2. Read **ENTIRE** task and identify **every** requirement (penalized for partial solutions)
3. Find and read files **IN FULL** before editing
4. Fix **root cause** with **smallest complete set of edits**
5. Match existing code style exactly
6. Hard rules: change **ONLY** what the task requires — no refactoring, cosmetics, reordering imports

**Submission sentinel:** `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`

### Architecture Summary

| Parameter | Value | Source |
|-----------|-------|--------|
| `DEFAULT_MAX_STEPS` | **50** | `os.environ.get("AGENT_MAX_STEPS", "50")` |
| `DEFAULT_COMMAND_TIMEOUT` | **15s** | `os.environ.get("AGENT_COMMAND_TIMEOUT", "15")` |
| `DEFAULT_MAX_TOKENS` | **8192** | `os.environ.get("AGENT_MAX_TOKENS", "8192")` |
| `MAX_OBSERVATION_CHARS` | **16000** | env `AGENT_MAX_OBSERVATION_CHARS` |
| `MAX_TOTAL_LOG_CHARS` | **260000** | env `AGENT_MAX_TOTAL_LOG_CHARS` |
| `WALL_CLOCK_LIMIT` | **TAU_AGENT_TIMEOUT_SECONDS - 20s** | Falls back to 280s |
| Format retries | **3 max** | `_MAX_FORMAT_RETRIES = 3` |
| Model retries | **5 attempts** | `max_attempts=5` in `ChatModel` |

### Multi-Shot Logic

**There is NO multi-shot wrapper in the king.** The king is:
- **Single-attempt**: one `run_agent_loop()` call per `solve()`
- **No retries on wrong answer** — one shot, done
- Up to 50 steps within that single attempt
- On crash: returns `collect_repo_patch()` as fallback (whatever diff exists on disk)

### Key Differences vs Old 20,889L King (e.g., adamninja PR#1551)

| Feature | Old King (~20K lines) | New King (684L flattened) |
|---------|----------------------|--------------------------|
| Multi-shot | ✅ Multiple attempts with WALL_CLOCK_BUDGET | ❌ Single attempt |
| Context gathering | ✅ Evidence priority chain, file reading heuristics | ❌ None — pure model-driven |
| TF-IDF / BM25 | ✅ Semantic file discovery | ❌ None |
| Test running | Sometimes | ❌ Explicitly forbidden ("do not run test suites") |
| SYSTEM_PROMPT length | Long, detailed persona | Short, minimal contract |
| Tool-call format | bash blocks only | bash blocks + native tool-call tokens |
| Wall clock handling | Complex budget management | `TAU_AGENT_TIMEOUT_SECONDS - 20s` from env |
| MAX_STEPS | 30 | 50 |
| Lines | ~20,889L (old monolith) | 684L flattened / ~550L canonical |

### What the King Does NOT Do (vs old approach)

1. **No context pre-loading**: doesn't read `git log`, `tree`, or project structure before starting
2. **No TF-IDF file ranking**: no intelligent file discovery
3. **No multi-shot**: if first attempt fails/produces bad patch, no retry
4. **No test validation**: hard rule against running test suites
5. **No reasoning-effort control**: cannot set `temperature`, `top_p`, etc. (blocked by validator)
6. **No sampling overrides**: completely at the mercy of validator-provided model
7. **No hardcoded model**: fully model-agnostic (model comes from validator)

### Native Tool-Call Fix (King's Secret Edge)

The king specifically handles models that emit native tool-call tokens:
```python
_NATIVE_TOOL_CALL_RE = re.compile(
    r"<\|tool_call_begin\|>(?P<name>.*?)<\|tool_call_argument_begin\|>(?P<args>.*?)<\|tool_call_end\|>",
    re.DOTALL,
)
```
This handles Kimi/Moonshot models that deviate from the bash-block contract. This was the critical change (`a56ffdf5`) that promoted it to king.

---

## 1c: Updated Submission Requirements

### Current Requirements (from MINER_SUBMISSION_CHECKLIST.md at king SHA)

**New Multi-File Submission Format:**
- `agent.py` (root) + `agent/` directory (supporting modules)
- `tau_agent_files.json` must list ALL bundle files
- Up to 32 `*.py` files, 5 MB max bundle size
- Single-file `agent.py` is still valid (backward compat)

**CI Gates (in order):**
1. **Signature Gate** — validates signed hotkey payload
2. **Registration Gate** — hotkey registered + not spent for this registration
3. **Agent Smoke** — compiles/imports every file, checks contract shape
4. **Submission Scope Guard** — checks each file for forbidden patterns
5. **OpenRouter Submission Judge** — `anthropic/claude-opus-4.7`, temperature 0, medium reasoning

**Forbidden Patterns (auto-reject):**
```
temperature|top_p|top_k|seed|presence_penalty|frequency_penalty|logit_bias|logprobs
sk-|Bearer |api_key\s*=\s*['"]|OPENROUTER|OPENAI_API_KEY|ANTHROPIC
```

**Contract Requirements:**
- `solve(repo_path, issue, model, api_base, api_key)` — exact signature
- Returns dict: `{patch, logs, steps, cost, success}`
- **No hardcoded model names** — must use `model` argument
- **No sampling controls** — proxy strips them, validator rejects agents that set them
- **Standard library only** — no third-party dependencies
- **No external network calls** outside the validator LLM proxy

**One Submission Per Registration (Critical):**
- Only ONE accepted submission per hotkey registration
- Second submission with same hotkey = rejected until fresh registration
- Multiple hotkeys under same coldkey CAN each submit their own bundles

**Quick Submission Command:**
```bash
python3 -m compileall -q agent.py agent
./scripts/check_agent_contract.py
python3 scripts/submit_private_submission.py \
  --wallet-name <wallet-name> \
  --wallet-hotkey <wallet-hotkey-name> \
  --hotkey <miner-hotkey-ss58>
```

---

## 1d: Scoring Formula Validation

### Live Scoring Formula (confirmed from dashboard.json)

```
scoring = {
    method: "race",
    duel_rounds: 50,
    win_margin: 6,
    patch_similarity_weight: 0.0,    # telemetry only
    cursor_similarity_weight: 0.0,   # telemetry only
    llm_diff_judge_weight: 0.95,
    solve_time_weight: 0.05,
    llm_diff_judge_model: "google/gemini-3.1-flash-lite",
    ties_count: False
}
```

**Round score formula (reverse-engineered from live duel data):**
```
round_score = 0.95 * llm_score + 0.05 * time_bonus
```

Where `time_bonus` ∈ [0, 1] is a normalized solve-time component (faster = higher).

**Evidence from active duel rounds:**

| Round | King LLM | King Score | King Time Bonus | Challenger LLM | Challenger Score | Challenger Time Bonus |
|-------|----------|------------|-----------------|----------------|------------------|-----------------------|
| 1 | 1.00 | 0.9982 | 0.964 | 1.00 | 0.9952 | 0.904 |
| 2 | 0.75 | 0.7598 | 0.946 | 0.95 | 0.9472 | 0.894 |
| 3 | 0.75 | 0.7601 | 0.952 | 0.85 | 0.8525 | 0.900 |
| 4 | 0.95 | 0.9425 | 0.800 | 0.20 | 0.2354 | 0.908 |
| 5 | 0.65 | 0.6587 | 0.824 | 0.30 | 0.3300 | 0.900 |
| 6 | 1.00 | 0.9979 | 0.958 | 1.00 | 0.9974 | 0.948 |
| 7 | 0.65 | 0.6575 | 0.800 | 0.95 | 0.9480 | 0.910 |

**Critical insight from time_bonus data:**
- Time bonus range ≈ 0.80 to 0.964 — consistently high (the models finish quickly)
- Time bonus difference between king and challenger is very small (0.004 to 0.06)
- **LLM score dominates completely**: a 0.20 LLM score difference (0.95 vs 0.75) = ~0.19 score difference; same LLM score with time diff ≈ 0.003 difference
- **solve_time_weight=0.05 is a continuous component, not a tie-break** — it always contributes, but its impact is tiny vs LLM quality

**Duel Win Logic:**
- **50 rounds** per duel, **ties ignored** (`ties_count=False`)
- **win_margin=6**: challenger must accumulate 6 MORE decisive wins than king
- "Threshold" in active_duel = minimum wins needed for mathematical replacement possibility
- Active duel threshold=11 ≈ (king_losses + win_margin) at current state

**LLM Scores are in steps of 0.05:**
- Observed values: 1.0, 0.95, 0.85, 0.75, 0.65, 0.3, 0.2
- Gemini Flash Lite scores in discrete 0.05 increments (0-100 integer → /100 → ~0.05 steps)

### Harness Gap: Judge Model Mismatch

**Live validator:** `google/gemini-3.1-flash-lite`  
**Our harness v6:** `anthropic/claude-sonnet-4.6` (hardcoded at line 72)

```
JUDGE_MODEL = "anthropic/claude-sonnet-4.6"   # validator_harness_v6.py:72
```

**Harness v6 does support `--judge-model` flag:**
```bash
python3 validator_harness_v6.py --challenger agent.py --judge-model google/gemini-3.1-flash-lite
```
**You can pass `--judge-model google/gemini-3.1-flash-lite` to get live-accurate gate results.**

**⚠️ IMPORTANT:** Harness v6 does NOT implement the solve_time_weight scoring. Its combined score is still `1.0 × llm_score` (PR#1598 LLM-only update). The harness is missing the 5% time component — but since it's only 5% of the score, gate thresholds remain valid.

**Harness v7 Notes:**  
- v7 exists at `validator_harness_v7_upstream.py` — more accurate reference/patch judge  
- v7 ALSO uses `1.0 × llm_score` (cursor_sim is telemetry per line 59)  
- Neither v6 nor v7 implements `solve_time_weight=0.05` — this is live-only  
- Gate thresholds should still be reliable since LLM score = 95% of outcome

---

## 1e: Live Duel Analysis (recent 30 duels vs new king)

### Current King Info
- **King:** `burn-uid-0` / `unarbos/ninja` base agent
- **King since:** 2026-06-14T06:51 UTC (~10 hours old at report time)
- **Defended:** 13 duels (0 replacements)

### Duel Win Rates (Challenger vs New King)

| Duel | W | L | T | Challenger WR | King Replaced |
|------|---|---|---|--------------|---------------|
| 6628 | 7 | 20 | 0 | **25%** | No |
| 6627 | 16 | 32 | 0 | **33%** | No |
| 6626 | 11 | 24 | 0 | **31%** | No |
| 6619 | 12 | 12 | 21 | **26%** (tie-heavy) | No |
| 6618 | 12 | 24 | 0 | **33%** | No |
| 6617 | 8 | 24 | 0 | **25%** | No |
| 6616 | 20 | 24 | 1 | **44%** | No |
| 6615 | 12 | 26 | 0 | **31%** | No |
| 6614 | 22 | 26 | 0 | **45%** | No |
| 6613 | 28 | 18 | 0 | **60%** | No |
| 6612 | 16 | 24 | 0 | **40%** | No |
| 6611 | 16 | 24 | 0 | **40%** | No |
| 6610 | 18 | 24 | 1 | **41%** | No |
| 6609 | 23 | 24 | 0 | **48%** | No |
| 6608 | 19 | 26 | 0 | **42%** | No |
| 6607 | 18 | 25 | 0 | **41%** | No |
| 6606 | 18 | 23 | 1 | **42%** | No |
| 6605 | 14 | 27 | 0 | **34%** | No |
| 6604 | 23 | 24 | 0 | **48%** | No |
| 6603 | 21 | 25 | 0 | **45%** | No |
| 6602 | 20 | 23 | 1 | **45%** | No |
| 6601 | 16 | 26 | 0 | **38%** | No |
| 6600 | 23 | 24 | 1 | **47%** | No |
| 6599 | 12 | 23 | 1 | **33%** | No |
| 6598 | 25 | 23 | 2 | **50%** | No |
| 6597 | 21 | 23 | 0 | **47%** | No |
| 6596 | 26 | 22 | 2 | **52%** | No |
| 6595 | 15 | 23 | 2 | **37%** | No |
| 6594 | 19 | 26 | 1 | **41%** | No |
| 6593 | 22 | 23 | 1 | **47%** | No |

### Statistical Summary

| Metric | Value |
|--------|-------|
| **Overall challenger WR (30 duels)** | **42.8%** (533W/712L) |
| **Per-duel WR range** | 25% – 61% |
| **Median per-duel WR** | ~42% |
| **King replacements** | **0** (13 duels defended with no replacement) |
| **Tie rate** | Low (~5-6% of rounds) |

### Analysis

**The new king is surprisingly strong despite being a CLEAN, MINIMAL agent.**  
No challengers have beaten it in 13 successive duels. The median WR of 42% means challengers are losing by ≈ 8% on average — in a 50-round duel this translates to losing by ~4 decisive rounds (king wins ~4 more than challenger). With win_margin=6, challengers need to flip 5+ rounds to win.

**Duel 6613 (60% WR) was the closest anyone got** but still didn't dethrone the king. The WR dropped sharply in more recent duels (6617: 25%, 6628: 25%), suggesting the queue contains many weak challengers but also that a small number of competitive agents exist.

**The "burn-uid-0" base agent is performing well because:**
1. Gemini Flash Lite rewards correct, complete patches over fancy context-gathering
2. The 50-step limit with simple bash tools is sufficient for most SWE tasks
3. The native tool-call regex fix handles edge case models that deviate from bash-block format

**What WR we need to beat it:** ~57-60% WR in our local gate (target 28+ wins out of 50 decisive rounds). Currently best challenger got 60% WR in one duel but didn't maintain it.

---

## 1f: Task Pool Status

### Dataset Location
- **V7 harness dataset:** `/root/sn66-r2-dataset/hf_dataset_cache.jsonl`  
- **V6 harness dataset:** `/root/sn66-ninja/hf_dataset_cache.jsonl` — **NOT FOUND** (missing)

### Dataset Stats
```
/root/sn66-r2-dataset/hf_dataset_cache.jsonl: 8,258 tasks
```
V7 harness references this dataset at `DATASET_PATH = "/root/sn66-r2-dataset/hf_dataset_cache.jsonl"`

The task pool is filtered and the v7 harness reports `9,122 filtered pool` in typical output — these 8,258 cached records represent the usable task pool.

### Live Duel Pool (from active duel)
```
active_duel.pool_size = 51
active_duel.gathered_tasks = 50
active_duel.needed_tasks = 50
```
The live validator uses fresh tasks from a smaller pool of 51 per duel window. Our harness will draw from the ~8,258 local R2 dataset.

### Task Pool Health
- ✅ **R2 dataset exists** at `/root/sn66-r2-dataset/hf_dataset_cache.jsonl` with 8,258 tasks
- ⚠️ **V6 harness dataset** (`/root/sn66-ninja/hf_dataset_cache.jsonl`) is missing — v6 gates will fail unless pointed to R2 dataset or the v7 harness is used instead
- The live validator uses fresh task generation; our local dataset is for gate testing only

---

## Synthesis: Top 5 Implications for Our Next Agent

### 1. **Match the King's Minimal Style, Then Beat It on LLM Score** (CRITICAL)

The king is a clean, minimal 50-step bash agent with NO special sauce beyond the bash/native-tool-call regex fix. It beats challengers because Gemini Flash Lite rewards **correct, complete patches** — not fancy multi-shot or context pre-loading. Our winning strategy is NOT to add complexity but to **produce better LLM scores on the same simple architecture**. The difference between winning and losing is almost entirely the LLM quality score (95% weight).

**Action:** Build a minimal agent similar to the king but with better code editing strategies (clearer step-by-step exploration, more targeted reads, better patch generation).

### 2. **Harness Must Use `--judge-model google/gemini-3.1-flash-lite`** (HIGH PRIORITY)

Our v6 harness defaults to `claude-sonnet-4.6` as judge. The live validator uses `google/gemini-3.1-flash-lite`. These models have different scoring biases. Our gate results are calibrated against the wrong model. To get accurate WR predictions:
```bash
python3 validator_harness_v6.py --challenger agent.py --king king_agent.py \
    --tasks 30 --judge-model google/gemini-3.1-flash-lite
```
Or migrate to v7 harness (more accurate in other respects too).

### 3. **Native Tool-Call Regex is Now Baseline — Don't Skip It**

The king's promotion commit was specifically `_NATIVE_TOOL_CALL_RE` to handle Kimi/Moonshot models. This is now in the base king, meaning our agent will be tested against a model that may emit native tool-call tokens. Our agent must also handle this format OR we risk format errors when tested with those models.

**The king also already incorporates** the latest `ae2158103232` logic concept (empty reply rejection) — but that commit is NEWER than the king, so the live king doesn't have it yet. Our next submission should include it.

### 4. **Dataset Issue: Use V7 Harness with R2 Dataset**

V6 harness is missing its local dataset. V7 harness is configured for `/root/sn66-r2-dataset/hf_dataset_cache.jsonl` which exists with 8,258 tasks. All gate testing should use v7 harness to avoid dataset issues AND get better judge accuracy.

```bash
python3 validator_harness_v7_upstream.py --challenger agent.py --king king_agent.py \
    --tasks 30 --seed 42
```

### 5. **Win Margin Is Achievable — The King Has a Gap at 40-45% LLM Score Tasks**

From the active duel data, the king struggles when its LLM score drops to 0.65-0.75 (rounds where king gets 0.65 LLM but challenger gets 0.95 = decisive challenger win). The king's weakness is **medium-hard tasks where its minimal exploration fails** — it doesn't pre-read files intelligently, so it sometimes submits patches that miss the root cause.

**Our edge:** Add one targeted improvement — better file discovery before editing. Read the file hierarchy, find the relevant file, read it IN FULL, then make a targeted edit. This costs ~2-3 steps but dramatically improves LLM score on the hard 30-40% of tasks where the king scores 0.65-0.75.

A well-targeted file-reading + editing strategy should push our WR from ~45% to 60%+ needed to beat the king.

---

## Raw Data Appendix

### Active Duel (6629) Rounds Detail
```
Round 1: king wins (both LLM=1.0, king faster: 0.9982 vs 0.9952)
Round 2: challenger wins (c_llm=0.95 vs k_llm=0.75)
Round 3: challenger wins (c_llm=0.85 vs k_llm=0.75)
Round 4: king wins (k_llm=0.95 vs c_llm=0.20)
Round 5: king wins (k_llm=0.65 vs c_llm=0.30)
Round 6: king wins (both LLM=1.0, king faster: 0.9979 vs 0.9974)
Round 7: challenger wins (c_llm=0.95 vs k_llm=0.65)
Score after 7 rounds: 3C/4K → challenger behind by 1
```

### King Package Structure
```
agent.py           (76 lines — thin solve() wrapper)
agent/__init__.py  (7 lines)
agent/agent_loop.py  (126 lines — step loop + native tool-call regex)
agent/environment.py (53 lines — subprocess bash executor)
agent/model.py       (109 lines — OpenAI chat client with retries)
agent/prompts.py     (131 lines — SYSTEM_PROMPT + TASK_TEMPLATE)
agent/repo_diff.py   (50 lines — git diff collector)
tau_agent_files.json (9 lines — bundle file list)
```

### Environment Variables Honored by King
```
AGENT_MAX_STEPS             (default: 50)
AGENT_COMMAND_TIMEOUT       (default: 15)
AGENT_MAX_TOKENS            (default: 8192)
AGENT_MAX_OBSERVATION_CHARS (default: 16000)
AGENT_MAX_TOTAL_LOG_CHARS   (default: 260000)
TAU_AGENT_TIMEOUT_SECONDS   (default: 280+20 = 300s)
AGENT_MODEL / NINJA_MODEL
AGENT_API_BASE / NINJA_INFERENCE_BASE_URL / OPENAI_BASE_URL
AGENT_API_KEY / NINJA_INFERENCE_API_KEY / OPENAI_API_KEY
```

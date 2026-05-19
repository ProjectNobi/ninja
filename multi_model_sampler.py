#!/usr/bin/env python3
"""
Multi-Model Gold Patch Sampler
Runs any LLM on all 9122 R2 tasks to build diverse training data.

Usage:
  python3 multi_model_sampler.py --model MiniMaxAI/MiniMax-M2.5-TEE --provider chutes
  python3 multi_model_sampler.py --model moonshotai/Kimi-K2.6-TEE --provider chutes
  python3 multi_model_sampler.py --model meta-llama/llama-3.3-70b-instruct --provider openrouter
  python3 multi_model_sampler.py --model glm-4.7-sweep2 --provider int2 --api-model glm-4.7 --output-file gold_patches_glm-4_7-sweep2.jsonl
  python3 multi_model_sampler.py --list-queue       # Show queued runs
  python3 multi_model_sampler.py --status           # Show progress on all runs

Key rotation (Chutes):
  CHUTES_API_KEY=cpk_xxx python3 multi_model_sampler.py ...  # single key via env
  python3 multi_model_sampler.py --key-file /root/project-nobi/scripts/chutes_keys.txt ...  # round-robin pool
"""

from __future__ import annotations
import argparse
import json
import os
import random
import re
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

# ─── Paths ────────────────────────────────────────────────────────────────────
R2_DATASET_PATH  = "/root/sn66-r2-dataset/hf_dataset_cache.jsonl"
OUTPUT_DIR       = Path("/root/sn66-ninja/training_data/gold_patches")
QUEUE_FILE       = OUTPUT_DIR / "multi_model_queue.json"

# ─── Key pool (round-robin for Chutes rate-limit avoidance) ───────────────────
_key_pool: List[str] = []
_key_index = 0

def load_key_file(path: str) -> None:
    """Load a key file (one key per line) into the global rotation pool."""
    global _key_pool, _key_index
    try:
        keys = [l.strip() for l in open(path) if l.strip()]
        if keys:
            _key_pool = keys
            _key_index = 0
            print(f"[KEY POOL] Loaded {len(keys)} keys from {path}")
    except Exception as e:
        print(f"[KEY POOL] Warning: could not load key file {path}: {e}")

def _next_key() -> Optional[str]:
    """Return next key in pool (round-robin). Returns None if pool empty."""
    global _key_index
    if not _key_pool:
        return None
    key = _key_pool[_key_index % len(_key_pool)]
    _key_index = (_key_index + 1) % len(_key_pool)
    return key

def _rotate_key_on_429() -> Optional[str]:
    """Move to the next key in pool after a 429. Returns new key or None."""
    global _key_index
    if len(_key_pool) <= 1:
        return None
    _key_index = (_key_index + 1) % len(_key_pool)
    key = _key_pool[_key_index]
    print(f"  [KEY ROTATE] Switching to key pool index {_key_index} after 429")
    return key

# ─── API Configs ──────────────────────────────────────────────────────────────
def get_api_config(provider: str) -> dict:
    if provider == "chutes":
        # Priority: key pool (--key-file) → env var → first line of default key file
        key = (_key_pool[_key_index % len(_key_pool)] if _key_pool else None) or \
              os.environ.get("CHUTES_API_KEY") or \
              open("/root/project-nobi/scripts/chutes_keys.txt").readline().strip()
        return {"base_url": "https://llm.chutes.ai/v1", "api_key": key}
    elif provider == "openrouter":
        key = os.environ.get("OPENROUTER_API_KEY") or \
              next((l.split("=",1)[1].strip().strip('"') for l in
                    open("/root/.secrets/api_keys.env") if "SN62_OPENROUTER" in l or "OPENROUTER_API_KEY" in l), "")
        return {"base_url": "https://openrouter.ai/api/v1", "api_key": key}
    elif provider == "t68s1":
        # Read actual API key from secrets
        key = os.environ.get("T68S1_API_KEY") or next((l.split("=",1)[1].strip() for l in
                    open("/root/.secrets/t68s1_api_key.env") if "T68S1_API_KEY" in l), "")
        return {"base_url": "http://localhost:8082/v1", "api_key": key}
    elif provider == "int2":
        key = next((l.split("=",1)[1].strip().strip('"') for l in
                    open("/root/.secrets/api_keys.env") if "INT2_API_KEY" in l), "")
        return {"base_url": "https://api.int2.net/v1", "api_key": key}
    else:
        raise ValueError(f"Unknown provider: {provider}")

# ─── Output file naming ───────────────────────────────────────────────────────
def model_to_filename(model: str) -> str:
    safe = re.sub(r'[^a-zA-Z0-9_-]', '_', model.replace('/', '_'))
    return f"gold_patches_{safe}.jsonl"

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert software engineer. Produce a git unified diff patch.

Output ONLY a valid unified diff starting with 'diff --git'. No explanation. /no_think"""

# ─── Task loading ─────────────────────────────────────────────────────────────
ARCHETYPES = {
    'FEATURE_BUILD': ['implement', 'add', 'create', 'feature', 'build', 'extend', 'enhance'],
    'BUG_FIX': ['fix', 'bug', 'error', 'issue', 'broken', 'incorrect', 'wrong', 'fail'],
    'REFACTOR': ['refactor', 'clean', 'restructure', 'simplify', 'improve', 'optimize'],
    'MIGRATION': ['migrate', 'update', 'upgrade', 'deprecat', 'replace', 'convert', 'move'],
}

def classify(text: str) -> str:
    text = text.lower()[:200]
    scores = {k: sum(1 for p in v if p in text) for k, v in ARCHETYPES.items()}
    return max(scores, key=scores.get)

def load_all_tasks(seed: int = 42) -> List[Dict]:
    random.seed(seed)
    tasks = []
    with open(R2_DATASET_PATH) as f:
        for i, line in enumerate(f, 1):
            try:
                r = json.loads(line)
                instr = r.get('instruction', '')
                ref = r.get('output', '')
                if not instr or not ref: continue
                tasks.append({
                    'task_id': f'r2_{i:05d}',
                    'archetype': classify(instr),
                    'source': 'r2',
                    'instruction': instr,
                    'reference_patch': ref,
                    'n_added_ref': len([l for l in ref.split('\n') if l.startswith('+')])
                })
            except: pass
    random.shuffle(tasks)
    return tasks

# ─── LLM call ─────────────────────────────────────────────────────────────────
# Models that need assistant prefill to avoid tool-call / exploration responses
PREFILL_MODELS = {
    "minimax/minimax-m2.5",
    "minimax/minimax-m2.7",
    "moonshotai/kimi-k2.6",
    "moonshotai/kimi-k2.5",
}

def call_llm(instruction: str, model: str, api_config: dict, timeout: int = 300,
             provider: str = "") -> Optional[str]:
    """Call LLM with exponential backoff on 429 and key rotation."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": instruction + " /no_think"},
    ]
    # Assistant prefill: force model to start with 'diff --git' for models
    # that tend to output tool-calls or exploration text (kimi-k2.6, minimax)
    if model in PREFILL_MODELS or any(m in model for m in ['minimax', 'kimi-k2.6']):
        messages.append({"role": "assistant", "content": "diff --git "})

    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": 4096,
    }
    # Only add Chutes-specific fields for Chutes provider
    if provider == "chutes" or provider == "t68s1":
        payload["temperature"] = 0.7
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    # t68s1 times out after ~90s per attempt; cap at 2 retries to avoid 466s wasted on each failure
    max_retries = 2 if provider == "t68s1" else 5
    backoff = 1.0
    for attempt in range(max_retries):
        # Refresh key on each attempt if key pool is active (for 429 rotation)
        current_key = api_config["api_key"]
        if _key_pool and provider == "chutes":
            current_key = _key_pool[_key_index % len(_key_pool)]

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{api_config['base_url']}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {current_key}",
                "Content-Type": "application/json",
                "User-Agent": "curl/7.88.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                msg = result["choices"][0]["message"]
                content = msg.get("content") or msg.get("reasoning_content") or ""
                return _extract_diff(content)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limited — rotate key and back off
                new_key = _rotate_key_on_429() if provider == "chutes" else None
                if new_key:
                    api_config = dict(api_config, api_key=new_key)
                wait = backoff * (2 ** attempt)
                wait = min(wait, 60.0)  # cap at 60s
                print(f"  [429] Rate limited. Attempt {attempt+1}/{max_retries}. "
                      f"Waiting {wait:.0f}s...", file=sys.stderr)
                time.sleep(wait)
            elif e.code in (500, 502, 503, 504):
                wait = backoff * (2 ** attempt)
                print(f"  [HTTP {e.code}] Server error. Attempt {attempt+1}/{max_retries}. "
                      f"Waiting {wait:.0f}s...", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  [HTTP {e.code}] {e}", file=sys.stderr)
                return None
        except Exception as e:
            wait = backoff * (2 ** min(attempt, 3))
            print(f"  [API ERROR] {e} (attempt {attempt+1}/{max_retries}, retry in {wait:.0f}s)",
                  file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(wait)

    print(f"  [FAILED] All {max_retries} attempts exhausted.", file=sys.stderr)
    return None

# Counter for logging empty responses (max 10)
_empty_log_count = 0
_empty_log_file = "/tmp/gemini_empty_responses.log"

def _extract_diff(text: str) -> Optional[str]:
    """Extract unified diff from LLM response. Handles multiple output formats."""
    global _empty_log_count
    if not text:
        return None

    # Step 0: Handle assistant prefill response — model continues after our 'diff --git ' prefix
    # The response may start with the path directly (e.g. 'a/file.py b/file.py\n---...')
    # Reconstruct the full diff header if missing
    stripped = text.strip()
    if stripped.startswith('a/') or stripped.startswith('b/') or stripped.startswith('--- a/'):
        text = 'diff --git ' + stripped

    # Step 1: Strip <think>...</think> blocks (DeepSeek/Qwen thinking models)
    cleaned = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE).strip()
    if not cleaned:
        cleaned = text

    # Step 2: Direct diff --git match (most models follow instructions)
    idx = cleaned.find("diff --git")
    if idx != -1:
        return cleaned[idx:].strip()

    # Step 3: Extract from ```diff code block (Gemini 3.1 Pro, Claude)
    m = re.search(r'```diff\s*\n([\s\S]+?)\n```', cleaned)
    if m:
        diff_content = m.group(1).strip()
        # Check if it contains a valid diff
        if '---' in diff_content and '+++' in diff_content:
            return diff_content

    # Step 4: Extract from generic ``` code block
    m = re.search(r'```(?:\w+)?\s*\n([\s\S]+?)\n```', cleaned)
    if m:
        diff_content = m.group(1).strip()
        if ('---' in diff_content and '+++' in diff_content) or diff_content.startswith('diff '):
            return diff_content

    # Step 5: Look for --- a/ / +++ b/ unified diff format anywhere in text
    m = re.search(r'((?:diff --git[^\n]*\n|)--- [^\n]+\n\+\+\+ [^\n]+\n@@[\s\S]+)', cleaned)
    if m:
        return m.group(1).strip()

    # Step 6: Log raw response for first 10 empties (debugging)
    if _empty_log_count < 10:
        _empty_log_count += 1
        try:
            with open(_empty_log_file, 'a') as f:
                f.write(f"=== EMPTY #{_empty_log_count} (len={len(text)}) ===\n")
                f.write(repr(text[:600]) + "\n\n")
        except Exception:
            pass

    return None

# ─── Main run ─────────────────────────────────────────────────────────────────
def run_model(model: str, provider: str, output_file_override: Optional[str] = None,
              api_model_override: Optional[str] = None, workers: int = 1, timeout: int = 300):
    api_config = get_api_config(provider)
    api_model = api_model_override or model  # actual model ID for API calls
    if output_file_override:
        output_file = OUTPUT_DIR / output_file_override if not os.path.isabs(output_file_override) else Path(output_file_override)
    else:
        output_file = OUTPUT_DIR / model_to_filename(model)
    tasks = load_all_tasks(seed=hash(model) % 10000)

    # Resume support
    done_ids = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                try: done_ids.add(json.loads(line)["task_id"])
                except: pass

    remaining = [t for t in tasks if t["task_id"] not in done_ids]
    n_total = len(tasks)
    n_done = len(done_ids)

    print(f"Model: {model}")
    print(f"Provider: {provider}")
    print(f"Output: {output_file}")
    print(f"Workers: {workers}")
    print(f"Tasks: {n_done}/{n_total} done, {len(remaining)} remaining")
    print()

    def _interrupt(sig, frame):
        print(f"\n[INTERRUPT] Progress saved.")
        sys.exit(0)
    signal.signal(signal.SIGINT, _interrupt)
    signal.signal(signal.SIGTERM, _interrupt)

    errors = 0
    run_start = time.time()
    write_lock = threading.Lock()
    counter_lock = threading.Lock()
    task_counter = [n_done]  # mutable counter for ETA
    error_counter = [0]

    def process_task(task):
        t_start = time.time()
        patch = call_llm(task["instruction"], api_model, api_config, provider=provider, timeout=timeout)
        elapsed = time.time() - t_start
        n_lines = len(patch.split("\n")) if patch else 0
        status = "✅" if patch and n_lines >= 3 else "❌"
        rec = {
            "task_id": task["task_id"],
            "archetype": task["archetype"],
            "source": "r2",
            "model": f"{provider}/{model}",
            "instruction": task["instruction"],
            "llm_patch": patch or "",
            "reference_patch": task["reference_patch"],
            "n_added_llm": n_lines,
            "n_added_ref": task.get("n_added_ref", 0),
            "elapsed_s": round(elapsed, 1),
        }
        with write_lock:
            with open(output_file, "a") as fout:
                fout.write(json.dumps(rec) + "\n")
        with counter_lock:
            task_counter[0] += 1
            if not patch:
                error_counter[0] += 1
            i = task_counter[0]
            elapsed_total = time.time() - run_start
            rate = i / elapsed_total if elapsed_total > 0 else 0
            eta_h = (n_total - i) / rate / 3600 if rate > 0 else 0
            print(f"[{i}/{n_total}] {task['task_id']} ({task['archetype']}) {status} {n_lines}L | {elapsed:.0f}s | ETA: {eta_h:.1f}h")

    if workers <= 1:
        for task in remaining:
            process_task(task)
    else:
        # Thread pool
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as executor:
            list(executor.map(process_task, remaining))

    print(f"\n✅ DONE: {model}")
    print(f"Errors: {error_counter[0]}/{n_total}")

# ─── Status / Queue ───────────────────────────────────────────────────────────
# Planned runs queue
PLANNED_RUNS = [
    # (model, provider, priority, note)
    ("MiniMaxAI/MiniMax-M2.5-TEE",            "chutes",      1, "80.2% SWE-bench — BEST available"),
    ("moonshotai/Kimi-K2.6-TEE",              "chutes",      2, "Latest Kimi, 76.8%+ SWE-bench"),
    ("moonshotai/Kimi-K2.5-TEE",              "chutes",      3, "76.8% SWE-bench"),
    ("deepseek-ai/DeepSeek-V3.2-TEE",         "chutes",      4, "Strong coder"),
    ("Qwen/Qwen3-Next-80B-A3B-Instruct-TEE",  "chutes",      5, "Qwen3-Coder-Next, coding specialist"),
    ("Qwen/Qwen3.5-397B-A17B-TEE",            "chutes",      6, "397B huge Qwen model"),
    ("zai-org/GLM-5.1-TEE",                   "chutes",      7, "Latest GLM"),
    ("Qwen/Qwen3-235B-A22B-Thinking-2507",    "chutes",      8, "235B with thinking"),
    ("meta-llama/llama-3.3-70b-instruct",     "openrouter",  9, "49% SWE-bench w/agent, ~$70"),
    ("google/gemma-3-27b-it",                 "openrouter", 10, "Google Gemma 3, ~$10"),
]

def show_status():
    print("=== Multi-Model Data Run Queue ===\n")
    total_done = 0
    total_target = 9122 * len(PLANNED_RUNS)
    for model, provider, priority, note in PLANNED_RUNS:
        out_file = OUTPUT_DIR / model_to_filename(model)
        if out_file.exists():
            done = sum(1 for _ in open(out_file))
            pct = done / 9122 * 100
            status = "✅ DONE" if done >= 9122 else f"🔄 {done}/9122 ({pct:.0f}%)"
        else:
            status = "⏳ NOT STARTED"
        total_done += done if out_file.exists() else 0
        print(f"  #{priority} [{provider.upper()}] {model}")
        print(f"     {note}")
        print(f"     Status: {status}")
    print(f"\nTotal progress: {total_done}/{total_target} patches")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="Model ID (used as label in records and default for API calls)")
    ap.add_argument("--provider", default="chutes", choices=["chutes","openrouter","t68s1","int2"])
    ap.add_argument("--api-model", dest="api_model", default=None,
                    help="Actual model ID to pass to the API (defaults to --model if not set)")
    ap.add_argument("--output-file", dest="output_file", default=None,
                    help="Custom output filename (default: auto-generated from model name). "
                         "Useful for resuming runs with non-standard filenames.")
    ap.add_argument("--key-file", dest="key_file", default=None,
                    help="Path to file with one Chutes API key per line (round-robin rotation)")
    ap.add_argument("--workers", type=int, default=1,
                    help="Number of parallel workers (default: 1)")
    ap.add_argument("--timeout", type=int, default=300,
                    help="LLM API timeout in seconds (default: 300)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--list-queue", action="store_true")
    args = ap.parse_args()

    # Load key pool if specified
    if args.key_file:
        load_key_file(args.key_file)
    elif args.provider == "chutes" and not os.environ.get("CHUTES_API_KEY"):
        # Auto-load default key file for Chutes runs if no env key set
        default_key_file = "/root/project-nobi/scripts/chutes_keys.txt"
        if os.path.exists(default_key_file):
            load_key_file(default_key_file)

    if args.status or args.list_queue:
        show_status()
    elif args.model:
        run_model(args.model, args.provider,
                  output_file_override=args.output_file,
                  api_model_override=args.api_model,
                  workers=args.workers,
                  timeout=args.timeout)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()

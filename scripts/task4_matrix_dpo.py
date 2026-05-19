#!/usr/bin/env python3
"""
SN66 Task 4: Full Model Matrix DPO Generator
Runs all scheduled model-pair comparisons from task4_pair_schedule.json.
Each pair: dual judge (GPT-5.4 + Sonnet) on common task_ids.

Priority tiers (from schedule):
  P1 — M2.7 vs top models (most valuable signal)
  P2 — Cross-family high-tier pairs
  P3 — Intra-family / lower-tier pairs

Usage:
  python3 task4_matrix_dpo.py --test              # first 5 pairs from P1
  python3 task4_matrix_dpo.py --priority 1        # P1 pairs only
  python3 task4_matrix_dpo.py --workers 8         # full run (all priorities)
  python3 task4_matrix_dpo.py --status
  python3 task4_matrix_dpo.py --list-pairs        # show schedule
  python3 task4_matrix_dpo.py --new-only          # skip pairs in ANY dpo file
  python3 task4_matrix_dpo.py --key-file /path/to/keys.txt  # OR key rotation
"""

from __future__ import annotations
import argparse, fcntl, hashlib, json, os, re, sys, time, threading
from pathlib import Path
from datetime import datetime, timezone

GOLD_DIR    = Path("/root/sn66-ninja/training_data/gold_patches")
SCHEDULE    = Path("/root/sn66-ninja/scripts/task4_pair_schedule.json")
OUTPUT_FILE = Path("/root/sn66-ninja/training_data/full_matrix_dpo_pairs.jsonl")
ALL_DPO_FILES = [
    Path("/root/sn66-ninja/training_data/reference_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/synthetic_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/self_play_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/full_matrix_dpo_pairs.jsonl"),
]
OR_BASE = "https://openrouter.ai/api/v1"
ANTHROPIC_BASE = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"
GPT54   = "openai/gpt-5.4"
SONNET  = "anthropic/claude-sonnet-4-6"
KIMI25        = "moonshotai/kimi-k2.5"

COST_PER_CALL = {GPT54: 0.029, SONNET: 0.006, KIMI25: 0.003}  # Kimi via OpenRouter

def _or_key() -> str:
    for path in ["/root/.secrets/gateway_extra.env", "/root/.secrets/api_keys.env"]:
        try:
            for line in open(path):
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=",1)[1].strip().strip('"')
        except: pass
    raise RuntimeError("No OPENROUTER_API_KEY found")


# ── Key pool with round-robin rotation ────────────────────────────────────────
_KEYS: list = []
_KEY_IDX = 0
_KEY_LOCK = threading.Lock()


_ANTHROPIC_KEY_CACHE = None
def _anthropic_key() -> str:
    global _ANTHROPIC_KEY_CACHE
    if _ANTHROPIC_KEY_CACHE:
        return _ANTHROPIC_KEY_CACHE
    for fpath in ["/root/.secrets/api_keys.env"]:
        try:
            for line in open(fpath):
                if line.startswith("ANTHROPIC_API_KEY="):
                    _ANTHROPIC_KEY_CACHE = line.split("=",1)[1].strip()
                    return _ANTHROPIC_KEY_CACHE
        except: pass
    raise RuntimeError("No ANTHROPIC_API_KEY found")

def _load_keys(key_file=None):
    """Load OR API keys from file or env. Returns list of keys."""
    global _KEYS
    keys = []
    if key_file and os.path.exists(key_file):
        with open(key_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and 'sk-or' in line:
                    keys.append(line)
        if keys:
            print(f"Key pool: {len(keys)} keys loaded from {key_file}", file=sys.stderr)
    if not keys:
        fallback = _or_key()
        keys = [fallback]
        print("Key pool: 1 key (from env)", file=sys.stderr)
    _KEYS = keys
    return keys

def _next_key() -> str:
    global _KEY_IDX
    with _KEY_LOCK:
        key = _KEYS[_KEY_IDX % max(1, len(_KEYS))]
        _KEY_IDX += 1
    return key


# ── Rate limiter: max N OR calls / 60s (scaled by key count) ──────────────────
class _RateLimiter:
    def __init__(self, max_calls: int = 50, window_sec: float = 60.0):
        self._lock   = threading.Lock()
        self._times: list[float] = []
        self._max    = max_calls
        self._window = window_sec

    def acquire(self):
        while True:
            with self._lock:
                now = time.time()
                self._times = [t for t in self._times if now - t < self._window]
                if len(self._times) < self._max:
                    self._times.append(now)
                    return
                wait = self._window - (now - self._times[0]) + 0.05
            time.sleep(wait)

# Default rate limiter — replaced in main() after key pool init
_rl = _RateLimiter(max_calls=50, window_sec=60.0)

import urllib.request, urllib.error

JUDGE_SYS = "You are an expert code reviewer. Respond ONLY with valid JSON."

def _judge_prompt(instr: str, pa: str, pb: str, ma: str, mb: str) -> str:
    return f"""Which patch better resolves this GitHub issue?

ISSUE: {instr[:1200]}

PATCH A ({ma}): {pa[:2500]}

PATCH B ({mb}): {pb[:2500]}

Judge: root cause fix, file coverage, acceptance criteria, code quality, completeness.
Respond ONLY with: {{"winner":"A" or "B","score_a":0.0-1.0,"score_b":0.0-1.0,"rationale":"2-3 sentences"}}"""

def _call_kimi(prompt: str, timeout: int = 120) -> dict:  # 120s: thinking model takes ~54s on real prompts
    """Call Kimi-K2.5 via OpenRouter — non-blocking 4th labeler. Uses same _next_key() pool as GPT54/Sonnet.
    NOTE: Kimi-K2.5 is a thinking model — content may be null while reasoning is populated.
    Fix: max_tokens=2048 (was 256, caused finish_reason=length before content), fallback to reasoning field."""
    _rl.acquire()
    key = _next_key()
    payload = json.dumps({
        "model": KIMI25,
        "messages": [
            {"role": "system", "content": JUDGE_SYS},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 2048,   # Kimi-K2.5 is a thinking model; 256 was too small (reasoning fills tokens)
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(
        f"{OR_BASE}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "curl/7.88.1"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        msg = json.loads(resp.read().decode())["choices"][0]["message"]
        # Kimi-K2.5 (thinking model): content may be null; check content then reasoning fallback
        content = msg.get("content") or msg.get("reasoning") or ""
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m: return json.loads(m.group())
        raise ValueError(f"No JSON from Kimi: {content[:100]}")


def process_pair(task_id: str, ra: dict, rb: dict,
                 label_a: str, label_b: str,
                 priority: int, verbose: bool = False) -> dict | None:
    instr = ra.get("instruction","")
    pa    = ra.get("llm_patch","") or ra.get("output","")
    pb    = rb.get("llm_patch","") or rb.get("output","")
    ma    = ra.get("model", label_a)
    mb    = rb.get("model", label_b)
    prompt = _judge_prompt(instr, pa, pb, label_a, label_b)
    try:
        g = _call(GPT54, prompt)
    except Exception as e:
        if verbose: print(f"  GPT err {task_id}: {e}", file=sys.stderr)
        return None
    try:
        s = _call_sonnet_direct(prompt)
    except Exception as e:
        if verbose: print(f"  Sonnet err {task_id}: {e}", file=sys.stderr)
        s = {}  # non-blocking: save pair with sonnet_winner="" and consensus=False

    gw = g.get("winner","").upper()
    sw = s.get("winner","").upper()
    consensus = gw == sw and gw in ("A","B")

    # Kimi-K2.5 — 4th labeler (non-blocking: SN66 may use Sonnet+Kimi as Phase 2 judges)
    km_winner = ""
    km_rationale = ""
    try:
        km = _call_kimi(prompt)
        km_winner = km.get("winner","").upper()
        km_rationale = km.get("rationale","")
    except Exception:
        pass  # non-blocking: failure doesn't affect existing data

    consensus_3 = (gw == sw == km_winner) and gw in ("A","B") if km_winner else None

    if   gw == "A": ca,cb,cl,rl_,sc,sr = ra,rb,label_a,label_b, g.get("score_a",.5), g.get("score_b",.5)
    elif gw == "B": ca,cb,cl,rl_,sc,sr = rb,ra,label_b,label_a, g.get("score_b",.5), g.get("score_a",.5)
    else:           return None

    rec = {
        "id":                   pair_id(task_id, label_a, label_b),
        "source":               "full_matrix",
        "task_id":              task_id,
        "instruction":          instr,
        "chosen_patch":         ca.get("llm_patch","") or ca.get("output",""),
        "rejected_patch":       cb.get("llm_patch","") or cb.get("output",""),
        "chosen_label":         cl,
        "rejected_label":       rl_,
        "gpt54_winner":         gw,
        "gpt54_score_chosen":   round(sc, 4),
        "gpt54_score_rejected": round(sr, 4),
        "sonnet_winner":        sw,
        "consensus":            consensus,
        "judge_rationale":      g.get("rationale",""),
        "sonnet_rationale":     s.get("rationale",""),
        "kimi25_winner":        km_winner,
        "kimi25_rationale":     km_rationale,
        "consensus_3":          consensus_3,  # True=all 3 agree (GPT54+Sonnet+Kimi25), None=Kimi unavailable
        "task_type":            classify(instr),
        "score_diff":           round(abs(g.get("score_a",.5)-g.get("score_b",.5)), 4),
        "priority":             priority,
        "collected_at":         datetime.now(timezone.utc).isoformat(),
        "est_cost_usd": round(COST_PER_CALL[GPT54] + COST_PER_CALL[SONNET] + (COST_PER_CALL[KIMI25] if km_winner else 0), 4),
    }
    if verbose:
        print(f"  ✅ {task_id} [{label_a} vs {label_b}]: winner={cl} "
              f"consensus={consensus} diff={rec['score_diff']:.2f}")
    return rec


def pair_id(task_id: str, ma: str, mb: str) -> str:
    h = hashlib.md5(f"matrix_{task_id}|{ma}|{mb}".encode()).hexdigest()[:12]
    return f"mat_dpo_{h}"

def load_model_file(path: Path) -> dict[str, dict]:
    data = {}
    if not path.exists():
        return data
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
                tid   = r.get("task_id","")
                patch = r.get("llm_patch","") or r.get("output","")
                if tid and patch and patch.strip():
                    data[tid] = r
            except: pass
    return data

def load_done(new_only: bool = False) -> set:
    done  = set()
    files = ALL_DPO_FILES if new_only else [OUTPUT_FILE]
    for f in files:
        if not f.exists(): continue
        with open(f) as fh:
            for line in fh:
                try: done.add(json.loads(line).get("id",""))
                except: pass
    return done

_wlock = threading.Lock()
def write_rec(r: dict):
    with _wlock:
        with open(OUTPUT_FILE, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.write(json.dumps(r) + "\n")
            fcntl.flock(f, fcntl.LOCK_UN)

def build_pairs_for_schedule_entry(entry: dict) -> list[tuple]:
    """Return list of (task_id, rec_a, rec_b, label_a, label_b) for a schedule entry."""
    fa = GOLD_DIR / entry["file_a"]
    fb = GOLD_DIR / entry["file_b"]
    if not fa.exists():
        print(f"  ⚠️  Missing: {fa.name}", file=sys.stderr); return []
    if not fb.exists():
        print(f"  ⚠️  Missing: {fb.name}", file=sys.stderr); return []
    da = load_model_file(fa)
    db = load_model_file(fb)
    common = sorted(set(da.keys()) & set(db.keys()))
    la = entry.get("label_a", fa.stem)
    lb = entry.get("label_b", fb.stem)
    return [(tid, da[tid], db[tid], la, lb) for tid in common]

def _init_pool_and_rl(key_file=None, n_workers=2):
    """Initialize key pool and rate limiter. Call at start of main() and --pair-files mode."""
    global _rl
    keys = _load_keys(key_file)
    n_keys = len(keys)
    # Scale rate limit by number of keys, but cap at 200 calls/min to avoid burst bans
    max_calls = min(50 * n_keys, 200)
    _rl = _RateLimiter(max_calls=max_calls, window_sec=60.0)
    print(f"Rate limit: {max_calls} calls/min ({n_keys} keys × 50) | workers: {n_workers}",
          file=sys.stderr)
    return keys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",       action="store_true", help="5 pairs from P1 only")
    parser.add_argument("--workers",    type=int, default=8, help="Parallel workers (default: 8)")
    parser.add_argument("--priority",   type=int, default=0,
                        help="Run only this priority tier (1/2/3). 0=all.")
    parser.add_argument("--status",     action="store_true")
    parser.add_argument("--list-pairs", action="store_true")
    parser.add_argument("--new-only",   action="store_true")
    parser.add_argument("--key-file",   default=None,
                        help="File with OR API keys (one per line). Enables key rotation.")
    parser.add_argument("--pair-files", nargs=2, metavar=("FILE_A", "FILE_B"),
                        help="Compare specific pair of gold files (called by feeder queue)")
    args = parser.parse_args()

    # ── Init key pool and rate limiter early ────────────────────────────────
    _init_pool_and_rl(args.key_file, args.workers)

    schedule = json.loads(SCHEDULE.read_text())["pairs"]
    # ── Direct pair-files mode (called from m27_patch_feeder.sh queue) ─────────
    if args.pair_files:
        fa = Path(args.pair_files[0])
        fb = Path(args.pair_files[1])
        if not fa.exists():
            print(f"ERROR: file not found: {fa}", file=sys.stderr); sys.exit(1)
        if not fb.exists():
            print(f"ERROR: file not found: {fb}", file=sys.stderr); sys.exit(1)
        la = fa.stem.replace("gold_patches_","")
        lb = fb.stem.replace("gold_patches_","")
        da = load_model_file(fa); db = load_model_file(fb)
        common = sorted(set(da.keys()) & set(db.keys()))
        done_set = load_done(new_only=args.new_only)
        pf_work = [(tid, da[tid], db[tid], la, lb, 99)
                    for tid in common if pair_id(tid, la, lb) not in done_set]
        print(f"[--pair-files] {la} vs {lb}: {len(pf_work)} pairs to process | Done: {len(done_set)}")
        if not pf_work: print("Nothing to do."); return
        pf_stats = {"done":0,"errors":0,"consensus":0,"cost_usd":0.0}
        pf_lock  = threading.Lock()
        w2 = min(args.workers, len(pf_work))
        chsz = (len(pf_work)+w2-1)//w2
        pf_chunks = [pf_work[i:i+chsz] for i in range(0, len(pf_work), chsz)]
        def _pf_worker(wlist):
            for tid, ra, rb, la_, lb_, prio in wlist:
                r = process_pair(tid, ra, rb, la_, lb_, prio, verbose=False)
                with pf_lock:
                    if r:
                        write_rec(r)
                        pf_stats["done"] += 1
                        pf_stats["consensus"] += int(r["consensus"])
                        pf_stats["cost_usd"] += r.get("est_cost_usd", 0.035)
                    else: pf_stats["errors"] += 1
                time.sleep(0.1)
        pf_threads = [threading.Thread(target=_pf_worker, args=(c,)) for c in pf_chunks]
        for t in pf_threads: t.start()
        for t in pf_threads: t.join()
        print(f"Done: {pf_stats['done']} | consensus={pf_stats['consensus']} | cost=${pf_stats['cost_usd']:.2f}")
        return


    if args.status:
        if OUTPUT_FILE.exists():
            lines    = [json.loads(l) for l in open(OUTPUT_FILE) if l.strip()]
            c        = sum(1 for l in lines if l.get("consensus"))
            cost     = sum(l.get("est_cost_usd",0.035) for l in lines)
            by_pri   = {}
            for l in lines:
                p = l.get("priority",0)
                by_pri[p] = by_pri.get(p,0) + 1
            print(f"Pairs: {len(lines)} | consensus: {c} | cost: ${cost:.2f}")
            for p in sorted(by_pri): print(f"  P{p}: {by_pri[p]}")
        else: print("No output yet.")
        return

    if args.list_pairs:
        for e in schedule:
            fa = GOLD_DIR / e["file_a"]
            fb = GOLD_DIR / e["file_b"]
            ca = sum(1 for _ in open(fa)) if fa.exists() else 0
            cb = sum(1 for _ in open(fb)) if fb.exists() else 0
            common_est = min(ca, cb)
            print(f"P{e['priority']} | {e['label_a']:<30} vs {e['label_b']:<30} | ~{common_est} common")
        return

    # ── Load all pairs from schedule ────────────────────────────────────────────
    done = load_done(new_only=args.new_only)
    all_work: list[tuple] = []  # (task_id, ra, rb, label_a, label_b, priority)
    filtered = [e for e in schedule if args.priority == 0 or e["priority"] == args.priority]
    for entry in filtered:
        p  = entry["priority"]
        for tid, ra, rb, la, lb in build_pairs_for_schedule_entry(entry):
            pid = pair_id(tid, la, lb)
            if pid not in done:
                all_work.append((tid, ra, rb, la, lb, p))

    if args.test:
        p1 = [x for x in all_work if x[5] == 1][:5]
        all_work = p1 if p1 else all_work[:5]

    print(f"Pairs to process: {len(all_work)} | Done: {len(done)}")
    print(f"Est cost: ${len(all_work)*0.035:.0f} @ $0.035/pair")

    if not all_work: print("Nothing to do."); return

    stats = {"done":0,"errors":0,"consensus":0,"cost_usd":0.0,"_total":len(all_work)}
    lock  = threading.Lock()
    w     = 1 if args.test else min(args.workers, len(all_work))
    chunk   = (len(all_work)+w-1)//w
    chunks  = [all_work[i:i+chunk] for i in range(0, len(all_work), chunk)]

    def worker(work_list: list):
        for tid, ra, rb, la, lb, prio in work_list:
            r = process_pair(tid, ra, rb, la, lb, prio, verbose=args.test)
            with lock:
                if r:
                    write_rec(r)
                    stats["done"]      += 1
                    stats["consensus"] += int(r["consensus"])
                    stats["cost_usd"]  += r.get("est_cost_usd", 0.035)
                    if stats["done"] % 50 == 0:
                        pct = stats["done"] / max(1, stats["_total"]) * 100
                        print(f"  📊 Progress: {stats['done']}/{stats['_total']} ({pct:.1f}%) | "
                              f"cost=${stats['cost_usd']:.2f} | consensus={stats['consensus']}")
                else:
                    stats["errors"] += 1
            time.sleep(0.1)   # reduced from 0.2 for higher throughput

    threads = [threading.Thread(target=worker, args=(c,)) for c in chunks]
    for t in threads: t.start()
    start = time.time()
    while any(t.is_alive() for t in threads):
        time.sleep(20)
        elapsed = (time.time()-start)/60
        total   = stats["done"]+stats["errors"]
        rate    = total/max(0.01,elapsed)
        eta     = (len(all_work)-total)/max(0.01,rate)
        print(f"[{elapsed:.0f}m] {total}/{len(all_work)} | ok={stats['done']} "
              f"err={stats['errors']} cost=${stats['cost_usd']:.2f} | ETA={eta:.0f}min")
    for t in threads: t.join()
    print(f"\n✅ Done: {stats['done']} | consensus={stats['consensus']} | cost=${stats['cost_usd']:.2f}")

if __name__ == "__main__": main()

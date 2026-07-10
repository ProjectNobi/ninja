#!/usr/bin/env python3
"""Score a gate run from its incremental JSONL, complete or not.

A gate run that dies partway used to be worth nothing: results lived in memory
and the summary only printed at the end. On 2026-07-09 one external kill at
~22:00 UTC ended all four KS42 runs (39/39/38/15 tasks at a near-identical
5.03-5.20 min/task) and 131 completed task duels went with it.

validator_harness_v7.py now flushes each result to GATE_RESULTS_JSONL as it
lands. This reads that file back.

    GATE_RESULTS_JSONL=/tmp/ks43_s7.jsonl bash scripts/gate.sh ... &
    python3 scripts/score_partial.py /tmp/ks43_s7.jsonl

A partial run is a PREFIX of the task list, not a random sample, so its delta is
biased by task order. Treat it as a progress signal, never as a submission gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

# See validator_harness_v7.py: the gate opponent is the burn baseline, not the
# live king, whose code is private. Provisional, from a single duel.
BURN_BASELINE_OFFSET = 0.089
DETHRONE_MARGIN = 0.05
FULL_RUN_TASKS = 50


def load(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                # A row torn in half by a kill mid-write. Only ever the last one.
                print(f"  ! dropped malformed row at line {n} (killed mid-write)",
                      file=sys.stderr)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("--expected", type=int, default=FULL_RUN_TASKS)
    args = ap.parse_args()

    rows = load(args.jsonl)
    if not rows:
        print("no results in file")
        return 1

    seen = {r.get("task_idx") for r in rows}
    n = len(rows)
    ch = [r.get("llm_score_challenger", 0.5) for r in rows]
    kg = [r.get("llm_score_king", 0.5) for r in rows]
    mean_ch, mean_kg = sum(ch) / n, sum(kg) / n
    delta = mean_ch - mean_kg
    live_equiv = delta - BURN_BASELINE_OFFSET

    winners = Counter(r.get("llm_winner", "tie") for r in rows)
    w = winners.get("challenger", 0)
    l = winners.get("king", 0)
    t = winners.get("tie", 0)

    ch_tok = sum(r.get("challenger_tokens", 0) or 0 for r in rows)
    kg_tok = sum(r.get("king_tokens", 0) or 0 for r in rows)

    complete = n >= args.expected
    print(f"\n  PARTIAL GATE SCORE  —  {args.jsonl}")
    print("  " + "─" * 63)
    print(f"  Tasks scored:      {n}/{args.expected}"
          f"{'  ✅ COMPLETE' if complete else '  ⚠️  PARTIAL (prefix, order-biased)'}")
    if len(seen) != n:
        print(f"  ! {n - len(seen)} duplicate task_idx — file appended across runs?")
    print(f"  Record:            {w}W-{l}L-{t}T")
    print(f"  Mean score:        ch={mean_ch:.4f}  king={mean_kg:.4f}  delta={delta:+.4f}")
    print(f"  Burn-calibrated:   live_delta ≈ {live_equiv:+.4f} "
          f"(gate − {BURN_BASELINE_OFFSET:.3f}; provisional)")
    if ch_tok or kg_tok:
        print(f"  Tokens/round:      ours {ch_tok/n:.0f}  king {kg_tok/n:.0f}")
    else:
        print("  Tokens/round:      not reported (agent predates token accounting)")

    by_type = {}
    for r in rows:
        key = r.get("task_type") or "?"
        hit = by_type.setdefault(key, [0, 0, 0])
        won = r.get("llm_winner", "tie")
        hit[0 if won == "challenger" else 1 if won == "king" else 2] += 1
    if len(by_type) > 1:
        print("\n  By task type:")
        for k, (tw, tl, tt) in sorted(by_type.items()):
            print(f"    {k:12s} {tw}W-{tl}L-{tt}T")

    print()
    if not complete:
        print("  Not a submission gate. Prefix ≠ sample; finish the run.")
    elif live_equiv >= DETHRONE_MARGIN:
        print(f"  Clears the calibrated bar (gate delta ≥ "
              f"{DETHRONE_MARGIN + BURN_BASELINE_OFFSET:+.3f}).")
    else:
        need = DETHRONE_MARGIN + BURN_BASELINE_OFFSET
        print(f"  Below the calibrated bar: need gate delta ≥ {need:+.3f}, have {delta:+.4f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

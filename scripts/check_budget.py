#!/usr/bin/env python3
"""Validate a challenger's effective wall-clock budget.

Imports the agent and calls the resolver, so the value is checked no matter
how it is spelled: a literal, a named constant, or an arithmetic expression.
A grep over the source cannot do this -- `float(28*10)` and
`return _FALLBACK_WALL_CLOCK` both hide 280.0 from a pattern match.

Usage:
    python3 scripts/check_budget.py agent_cl_gpt_KingSlayer41.py
"""
import argparse
import importlib.util
import os
import sys

MAX_FALLBACK = 270.0   # 300s SIGKILL - 30s reserve for the return path
MIN_RESERVE = 30.0


def load(path):
    spec = importlib.util.spec_from_file_location("challenger", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["challenger"] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("agent", help="Path to challenger .py file")
    args = ap.parse_args()

    # Live duels do not pass the timeout env var; the fallback is what runs.
    for k in list(os.environ):
        if k.startswith("TAU_AGENT_"):
            del os.environ[k]

    try:
        mod = load(args.agent)
    except Exception as e:
        print(f"BUDGET CHECK FAILED: could not import agent: {e}")
        return 1

    resolver = next(
        (getattr(mod, n) for n in ("_resolve_wall_clock", "_wall_clock_limit_seconds")
         if hasattr(mod, n)),
        None,
    )
    if resolver is None:
        print("BUDGET CHECK FAILED: no wall-clock resolver found "
              "(_resolve_wall_clock or _wall_clock_limit_seconds)")
        return 1

    try:
        effective = float(resolver())
    except Exception as e:
        print(f"BUDGET CHECK FAILED: resolver raised: {e}")
        return 1

    reserve = 0.0
    for attr in ("_WALL_CLOCK_RESERVE_SECONDS", "_WALL_CLOCK_MARGIN"):
        if hasattr(mod, attr):
            try:
                reserve = float(getattr(mod, attr))
                break
            except (TypeError, ValueError):
                pass

    ok = True
    if effective > MAX_FALLBACK:
        print(f"BUDGET CHECK FAILED: effective fallback = {effective}s "
              f"(max {MAX_FALLBACK}s)")
        print("  300s SIGKILL leaves no reserve for the return path.")
        ok = False
    if reserve < MIN_RESERVE:
        print(f"BUDGET CHECK FAILED: reserve = {reserve}s (min {MIN_RESERVE}s)")
        ok = False

    if ok:
        print(f"Budget check OK (effective fallback={effective}s, reserve={reserve}s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

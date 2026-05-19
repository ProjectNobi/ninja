#!/usr/bin/env python3
"""
SN66 DPO → Unified Gold Migration Script
Converts new DPO pairs from all four DPO output files into the unified
training_unified_gold.jsonl schema and appends them (deduped by task_id+source).

Unified schema:
  instruction   — issue/task description
  output        — chosen_patch (the winning diff)
  llm_response  — rejected_patch (losing diff, useful for contrastive signal)
  model         — chosen_label (who produced the winner: reference/m2.7/model-name)
  archetype     — inferred from task_type
  source        — DPO source tag (reference_vs_m2.7 / synthetic_dual_judge / etc.)
  task_type     — BUGFIX / UPDATE / FEATURE / API
  edit_quality  — derived from score_diff + consensus
  is_winner     — always True (we only migrate chosen_patch records)

AnonServer is source of truth — originals NEVER deleted.
Hetzner1 = copy for fine-tuning pipeline.

Usage:
  python3 migrate_dpo_to_unified.py --dry-run        # preview counts, no writes
  python3 migrate_dpo_to_unified.py                  # migrate new records
  python3 migrate_dpo_to_unified.py --status         # show migration state
  python3 migrate_dpo_to_unified.py --reset-state    # clear seen IDs (re-migrate all)
"""

from __future__ import annotations
import argparse, fcntl, json, sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
UNIFIED_GOLD = Path("/root/sn66-ninja/training_data/training_unified_gold.jsonl")
STATE_FILE   = Path("/root/sn66-ninja/training_data/.dpo_migrate_state.json")

DPO_FILES = [
    Path("/root/sn66-ninja/training_data/reference_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/synthetic_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/self_play_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/full_matrix_dpo_pairs.jsonl"),
    Path("/root/sn66-ninja/training_data/update_task_dpo_pairs.jsonl"),  # added 2026-05-19
    Path("/root/sn66-ninja/training_data/glm47_sweep7_dpo.jsonl"),        # added 2026-05-19
]

# ── Archetype mapping (task_type → archetype) ──────────────────────────────────
ARCHETYPE_MAP = {
    "BUGFIX":  "BUG_FIX",
    "UPDATE":  "REFACTOR",
    "API":     "API_CHANGE",
    "FEATURE": "FEATURE_BUILD",
}

# ── Edit quality thresholds ────────────────────────────────────────────────────
def _edit_quality(score_diff: float, consensus: bool) -> str:
    """
    Map judge score_diff + consensus flag to edit_quality label.
      excellent  — large margin, both judges agree
      good       — clear margin or strong consensus
      moderate   — moderate signal
      borderline — low margin or judges disagree
    """
    if score_diff >= 0.35 and consensus:  return "excellent"
    if score_diff >= 0.20:                return "good"
    if score_diff >= 0.10:                return "moderate"
    return "borderline"

# ── Schema conversion ──────────────────────────────────────────────────────────
def dpo_to_unified(rec: dict) -> dict | None:
    """Convert a single DPO record to unified schema. Returns None if record invalid."""
    chosen  = rec.get("chosen_patch","").strip()
    rejected = rec.get("rejected_patch","").strip()
    instr   = rec.get("instruction","").strip()
    if not chosen or not instr:
        return None

    task_type = rec.get("task_type","FEATURE").upper()
    archetype = ARCHETYPE_MAP.get(task_type, "FEATURE_BUILD")
    score_diff = float(rec.get("score_diff", 0.0))
    consensus  = bool(rec.get("consensus", False))

    return {
        "instruction":  instr,
        "output":       chosen,
        "llm_response": rejected,                      # contrastive signal
        "model":        rec.get("chosen_label", "dpo"),
        "archetype":    archetype,
        "source":       rec.get("source", "dpo"),
        "task_type":    task_type,
        "edit_quality": _edit_quality(score_diff, consensus),
        "is_winner":    True,
        # migration provenance (not in original schema but harmless extras)
        "_dpo_id":      rec.get("id",""),
        "_task_id":     rec.get("task_id",""),
        "_score_diff":  score_diff,
        "_consensus":   consensus,
        "_migrated_at": datetime.now(timezone.utc).isoformat(),
    }

# ── State management ───────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except: pass
    return {"seen_ids": [], "last_run": None, "total_migrated": 0}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Append to unified gold (file-locked, atomic) ───────────────────────────────
def append_records(records: list[dict]) -> int:
    if not records:
        return 0
    with open(UNIFIED_GOLD, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        for r in records:
            f.write(json.dumps(r) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)
    return len(records)

# ── JSONL validation ───────────────────────────────────────────────────────────
def validate_jsonl(path: Path) -> tuple[int, int]:
    """Returns (valid_lines, corrupt_lines)."""
    valid = corrupt = 0
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                json.loads(line); valid += 1
            except: corrupt += 1
    return valid, corrupt

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",     action="store_true", help="Preview only, no writes")
    parser.add_argument("--status",      action="store_true", help="Show migration state")
    parser.add_argument("--reset-state", action="store_true", help="Clear seen IDs (re-migrate all)")
    parser.add_argument("--validate",    action="store_true", help="Validate all DPO files + unified gold")
    args = parser.parse_args()

    if args.validate:
        print("Validating JSONL files...")
        for f in DPO_FILES + [UNIFIED_GOLD]:
            if not f.exists(): print(f"  ⚪ {f.name}: not found"); continue
            v, c = validate_jsonl(f)
            status = "✅" if c == 0 else "❌"
            print(f"  {status} {f.name}: {v} valid, {c} corrupt")
        return

    state = load_state()

    if args.reset_state:
        state = {"seen_ids": [], "last_run": None, "total_migrated": 0}
        save_state(state)
        print("State reset. Re-run without --reset-state to migrate all records.")
        return

    if args.status:
        gold_lines = sum(1 for _ in open(UNIFIED_GOLD)) if UNIFIED_GOLD.exists() else 0
        dpo_totals = {}
        for f in DPO_FILES:
            dpo_totals[f.name] = sum(1 for _ in open(f)) if f.exists() else 0
        print(f"Migration state:")
        print(f"  Last run:       {state.get('last_run','never')}")
        print(f"  Total migrated: {state.get('total_migrated',0)}")
        print(f"  Seen IDs:       {len(state.get('seen_ids',[]))}")
        print(f"  Unified gold:   {gold_lines} records")
        print(f"  DPO files:")
        for name, count in dpo_totals.items():
            print(f"    {name}: {count}")
        return

    seen_ids = set(state.get("seen_ids", []))
    to_migrate: list[dict] = []
    new_ids:    list[str]  = []
    skipped = 0

    for dpo_file in DPO_FILES:
        if not dpo_file.exists():
            print(f"  ⚪ Skipping (not found): {dpo_file.name}")
            continue

        file_new = file_skipped = 0
        with open(dpo_file) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    print(f"  ⚠️  Corrupt line in {dpo_file.name} — skipping", file=sys.stderr)
                    continue

                rec_id = rec.get("id","")
                if not rec_id or rec_id in seen_ids:
                    file_skipped += 1
                    skipped += 1
                    continue

                unified = dpo_to_unified(rec)
                if unified is None:
                    file_skipped += 1
                    skipped += 1
                    continue

                to_migrate.append(unified)
                new_ids.append(rec_id)
                file_new += 1

        print(f"  {dpo_file.name}: {file_new} new, {file_skipped} already seen")

    print(f"\nSummary: {len(to_migrate)} records to migrate | {skipped} already seen/invalid")

    if args.dry_run:
        if to_migrate:
            print(f"\n[DRY RUN] Would append {len(to_migrate)} records to {UNIFIED_GOLD.name}")
            print("Sample unified record:")
            sample = to_migrate[0]
            for k, v in sample.items():
                val = str(v)[:80] if isinstance(v, str) else v
                print(f"  {k}: {val}")
        else:
            print("[DRY RUN] Nothing to migrate.")
        return

    if not to_migrate:
        print("Nothing new to migrate.")
        return

    # Validate new records before appending
    bad = [r for r in to_migrate if not r.get("output") or not r.get("instruction")]
    if bad:
        print(f"  ⚠️  {len(bad)} records failed validation (empty output/instruction) — skipping them")
        to_migrate = [r for r in to_migrate if r.get("output") and r.get("instruction")]

    written = append_records(to_migrate)

    # Update state
    state["seen_ids"]       = list(seen_ids | set(new_ids))
    state["last_run"]       = datetime.now(timezone.utc).isoformat()
    state["total_migrated"] = state.get("total_migrated", 0) + written
    save_state(state)

    gold_total = sum(1 for _ in open(UNIFIED_GOLD)) if UNIFIED_GOLD.exists() else 0
    print(f"\n✅ Migrated {written} records → {UNIFIED_GOLD.name}")
    print(f"   Unified gold total: {gold_total}")
    print(f"   Migration state saved: {STATE_FILE.name}")

if __name__ == "__main__": main()

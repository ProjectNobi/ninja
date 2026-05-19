#!/usr/bin/env python3
"""
Incremental save of ALL running gold patch sets to unified data collector.
Runs every few hours to keep unified gold current even during long data runs.
Saves what's available NOW — partial runs are valuable too.

James directive 2026-05-14: Save ALL running data runs to unified gold continuously.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

GOLD_DIR = Path('/root/sn66-ninja/training_data/gold_patches')
UNIFIED = Path('/root/sn66-ninja/training_data/training_unified_gold.jsonl')
REGISTRY = Path('/root/sn66-ninja/training_data/runs_registry.jsonl')
SAVE_STATE = Path('/root/sn66-ninja/training_data/incremental_save_state.json')

NOW = datetime.now(timezone.utc).isoformat()

def load_save_state():
    """Track how many records were already saved per file."""
    if SAVE_STATE.exists():
        return json.load(open(SAVE_STATE))
    return {}

def save_save_state(state):
    SAVE_STATE.write_text(json.dumps(state, indent=2))

def load_unified_index():
    """Build index of (source, task_id) already in unified gold."""
    index = set()
    if UNIFIED.exists():
        with open(UNIFIED) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    key = f"{r.get('source','?')}::{r.get('task_id','?')}"
                    index.add(key)
                except: pass
    return index

def get_source_id(filepath: Path) -> str:
    """Generate consistent source ID from filename."""
    name = filepath.stem
    # Clean up the auto-generated names
    name = name.replace('gold_patches_', '')
    # Truncate to reasonable length
    return name[:60]

def main():
    print(f"=== Incremental Save to Unified Gold ===")
    print(f"Time: {NOW}")
    print()

    state = load_save_state()
    unified_index = load_unified_index()
    current_unified_count = sum(1 for _ in open(UNIFIED)) if UNIFIED.exists() else 0
    print(f"Unified gold before: {current_unified_count:,} records")

    # All gold patch files to process
    all_files = (
        list(GOLD_DIR.glob('gold_patches_*.jsonl')) +
        list(GOLD_DIR.glob('glm47*.jsonl')) +
        list(GOLD_DIR.glob('qwen3b*.jsonl')) +
        # s-series challenger/gold files (s7b, s10, s11b, s12b, s13b, s14b, s15b, s16b, etc.)
        list(GOLD_DIR.glob('s[0-9]*.jsonl'))
    )
    # Deduplicate (in case any file matches multiple globs)
    seen_paths = set()
    deduped = []
    for f in all_files:
        if f not in seen_paths:
            seen_paths.add(f)
            deduped.append(f)
    all_files = [f for f in deduped if f.exists() and not f.name.endswith('.bak')]

    total_added = 0
    total_skipped = 0
    run_summaries = []

    with open(UNIFIED, 'a') as fout:
        for fpath in sorted(all_files):
            source_id = get_source_id(fpath)
            prev_saved = state.get(source_id, 0)

            records_in_file = sum(1 for _ in open(fpath))
            new_records = records_in_file - prev_saved

            if new_records <= 0:
                run_summaries.append({
                    'source': source_id, 'total': records_in_file,
                    'new_added': 0, 'status': 'no_new'
                })
                continue

            added = skipped = 0
            with open(fpath) as fin:
                for idx, line in enumerate(fin):
                    if idx < prev_saved:
                        continue  # Skip already-saved records
                    try:
                        r = json.loads(line.strip())
                        task_id = r.get('task_id', f'idx_{idx}')
                        model = r.get('model', source_id)
                        llm_patch = r.get('llm_patch', '')
                        ref_patch = r.get('reference_patch', '')

                        # Skip empty llm patches (no training signal)
                        if not llm_patch.strip():
                            skipped += 1
                            continue

                        # Skip duplicates within same model+task
                        dedup_key = f"{source_id}::{task_id}"
                        if dedup_key in unified_index:
                            skipped += 1
                            continue

                        unified_index.add(dedup_key)

                        rec = {
                            'instruction': r.get('instruction', ''),
                            'output': ref_patch,
                            'llm_response': llm_patch,
                            'model': model,
                            'archetype': r.get('archetype', ''),
                            'source': source_id,
                            'task_id': task_id,
                        }
                        fout.write(json.dumps(rec) + '\n')
                        added += 1
                    except: pass

            state[source_id] = records_in_file  # Update cursor
            total_added += added
            total_skipped += skipped

            run_summaries.append({
                'source': source_id,
                'total_in_file': records_in_file,
                'new_added': added,
                'new_skipped': skipped,
                'status': 'saved'
            })
            print(f"  ✅ {source_id}: +{added} new records (file total: {records_in_file})")

    # Save state
    save_save_state(state)

    # Update registry
    if total_added > 0:
        entry = {
            'run_id': f'incremental_save_{NOW[:10]}',
            'timestamp_utc': NOW,
            'source_files': [str(f) for f in all_files],
            'records': total_added,
            'king_at_time': 'running',
            'added_to_unified': True,
            'notes': f'Incremental save. {len(all_files)} files processed. {total_added} new records.',
        }
        with open(REGISTRY, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    new_count = sum(1 for _ in open(UNIFIED)) if UNIFIED.exists() else 0
    print()
    print(f"=== SAVE COMPLETE ===")
    print(f"  New records added:   {total_added:,}")
    print(f"  Skipped (dup/empty): {total_skipped:,}")
    print(f"  Unified gold before: {current_unified_count:,}")
    print(f"  Unified gold after:  {new_count:,}")
    print(f"  Net gain:            +{new_count - current_unified_count:,}")

    # Print per-file summary
    print()
    print("Per-file summary:")
    for s in run_summaries:
        if s.get('new_added', 0) > 0:
            print(f"  {s['source'][:45]}: +{s['new_added']} / {s.get('total_in_file', s.get('total', '?'))}")

if __name__ == '__main__':
    main()

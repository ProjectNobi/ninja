# SN66 Live Duel Analysis — v69 Root Cause Report
*Generated 2026-05-19 13:25 UTC from duels 5167, 5166, 5165, 5158*

## Our Agents and Results
| Duel | Agent | Score | King Replaced |
|------|-------|-------|---------------|
| 5167 | v68 | 23W-23L-2T | ❌ NO |
| 5166 | v67-re | 21W-24L-2T | ❌ NO |
| 5165 | v67 | 19W-25L-0T | ❌ NO |
| 5158 | unknown | 21W-24L-0T | ❌ NO |

## 🔴 CRITICAL: 12 Tasks We Lose in ALL 4 Duels
These are FIXED tasks in the current pool — the king has been specifically optimized for these:
- 064765 (Dart/Flutter MCP) — timeout loss, ch=0.94-0.95 vs k=0.97
- 064761, 064747, 064757, 064767 — consistent losses
- 064811 (large feature, timeout) — ch_lines<<k_lines
- 064771, 064774, 064714, 064706 — under-editing losses
- 064745, 064730 — major under-editing (ch=455 vs k=7720)

## Root Cause 1: TIMEOUT LOSSES (13 total)
- `time_limit_exceeded` on complex tasks
- Task 064765: we output 9395 lines but score 0.94 vs king 0.97 → TIMEOUT at end
- Task 064811: timeout → ch_lines way below king (3982 vs 6922)
- Task 064757: complete timeout → ch_lines=0 vs king=2657
- **Pattern**: Large/complex tasks where our agent runs out of time

## Root Cause 2: MASSIVE UNDER-EDITING on Large Feature Tasks
- Task 064730: ch=455 vs k=7720 — we output 17× FEWER lines, score gap=0.70
- Task 064694: ch=0 vs k=7047 — completely empty patch
- Task 064706: ch=1238 vs k=8450 — score gap=0.58
- Task 064828: ch=147 vs k=2791 — score gap=0.54
- **Pattern**: Large FEATURE_BUILD tasks requiring comprehensive multi-file changes

## Root Cause 3: NARROW MARGIN LOSSES (Dart/Flutter specific)
- Task 064765: ch=0.94-0.95 vs k=0.97 — king matches reference exactly inc. import ordering
- King has explicit Dart/Flutter rules (line 2963 in king_agent.py)
- Our agents miss screen files, import ordering, package paths

## Root Cause 4: SCORE DISTRIBUTION
- Avg loss gap: 0.198 | Median: 0.140
- Close losses (< 0.05): 5 — nearly tied but king wins on margin requirement
- Big losses (>= 0.2): 35 — large quality gaps on feature tasks

## Key Rationale Patterns (from judge):
- "King implements the full feature nearly identically to reference"
- "challenger critically missing [specific component]"
- "Both miss some details but challenger misses more"
- "King matches reference exactly including import ordering"
- "Challenger patch is completely empty, scoring 0"

## Task Type Distribution (live duels ~May 9-19 pool)
Same task IDs appear across all 4 duels → FIXED pool still (rotation starts this week)
Primary failure modes in fixed pool: large FEATURE_BUILD + Dart/Flutter tasks

## King Strengths (what we need to match)
1. Dart/Flutter expert rules — screen files, package imports, specific patterns
2. Time management — king never times out
3. Full-feature implementation — produces comprehensive patches for large tasks
4. Reference alignment — matches exact import ordering, structure

## v69 Build Priorities
1. **Fix timeout** — better time budgeting, early commit on partial work
2. **Fix under-editing** — completeness check before finalizing, multi-file expansion
3. **Dart/Flutter rules** — adopt king's specific Dart/Flutter patterns (line 2963+)
4. **UPDATE task improvement** — gate test shows only 14% WR on UPDATE

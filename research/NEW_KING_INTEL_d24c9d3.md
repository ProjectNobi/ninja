# New King Intel — UID 64, commit d24c9d3 (2026-05-18)

## What Changed vs Previous King (6abf172)

### REMOVED (old king had, new king doesn't)
- `_strip_minified_content_diffs()` — minified content filtering
- `_issue_error_string_boost()` — error string file relevance boosting

### ADDED (new king has, we don't)

#### 1. `_patch_ship_blockers(patch, issue)` — Structural gap detector
Detects 5 gaps that correlate with losing duels:
- `empty_patch` — patch is empty
- `required_paths_uncovered` — patch doesn't touch files the issue mentions
- `missing_required_deletions` — issue implies deletion but patch has none
- `relocation_incomplete` — issue implies file move but no new files created
- `criteria_mostly_unaddressed` — 2+ acceptance criteria unaddressed

#### 2. `_patch_duel_score(patch, issue)` — Candidate scoring
Ranks patches for multi-shot selection (higher = better):
- +10 per substantive change
- +30 if covers required paths
- +35 minus 12× unaddressed criteria count
- +20 if correctly handles deletions when required
- +25 if correctly handles relocations when required
- -18 per ship blocker found

#### 3. `build_ship_blocker_prompt(blockers, issue)` — Fix guidance
Tells the agent exactly which gaps to fix in the retry attempt.

#### 4. `_companion_test_timeout_seconds(command_timeout, remaining_seconds)` — Smart test budget
Scales companion test timeout with remaining wall-clock time.
Returns 8-14 seconds, scales with remaining_seconds // 6.

#### 5. `_suggest_targeted_test_command(repo, patch)` — Smart test selection
Returns correct test command per file type:
- .py → `pytest {partner} -x -q --tb=short`
- .ts/.tsx/.js/.jsx → `npm test -- {partner}`
- .go → `go test {pkg} -count=1`
- .rs → `cargo test --offline -q`

### Multi-Shot Flow (new king's solve() logic)
```
attempt1 → _patch_ship_blockers() → if blockers: inject fix prompt → attempt2
_score1 = _patch_duel_score(attempt1)
_score2 = _patch_duel_score(attempt2)
if score2 > score1: use attempt2 else use attempt1
```

## What v63 Must Have
1. Port `_patch_ship_blockers()`, `_patch_duel_score()`, `build_ship_blocker_prompt()` from king
2. Port `_companion_test_timeout_seconds()` and `_suggest_targeted_test_command()` from king
3. Implement proper multi-shot: attempt1 → score → if blockers → attempt2 → pick better score
4. Keep v62 improvements: MAX_STEPS=50, MAX_COMMANDS=25, UPDATE WIRING RULE, LANGUAGE RULES, COMPLETENESS asymmetry

## Expected Impact
- Ship blocker detection catches the 5 most common loss patterns BEFORE submitting
- Multi-shot with scoring picks the better patch systematically
- Smart test commands improve cursor_sim (test files verified correctly)
- Estimated WR improvement over v62: +5-8% (conservative)

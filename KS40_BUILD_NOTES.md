# KS40 Build Notes — Dragon Lord 🐉

**File:** `agent_cl_gpt_KingSlayer40.py`  
**Base:** `agent_cl_gpt_KingSlayer39_hung.py` (1943 lines)  
**Output:** 2220 lines (+277 lines, all new KS40 additions)  
**Compile:** OK (`python3 -m py_compile` + `ast.parse` both pass)  
**Branch:** `kingslayer/ks40`  

---

## Summary

KS40 adds 6 targeted changes on top of the byte-identical KS39 base. Zero KS39 proven-advantage code was modified. All changes are additive except the completeness gate modification (Change 6) which is a guarded skip, not a removal.

---

## Change 1 — `run_best_of_two_ks40()` Reroll Orchestrator

**Priority:** HIGHEST  
**Lines added:** ~130 lines (constants + 5 helper functions + main orchestrator)

### Constants (line 98–102)
```
_KS40_REROLL_MIN_REMAINING = 160.0
_KS40_REROLL_MARGIN = 100.0
_KS40_REROLL_MIN_WALL = 60.0
_KS40_MATERIALIZE_MIN = 15.0
```

### Helper functions
| Function | Line | Purpose |
|----------|------|---------|
| `_patch_key_ks40()` | 1778 | Quality key tuple matching king's `_key()` |
| `_git_out_ks40()` | 1835 | Run git command, return stdout or None |
| `_git_reset_verify_ks40()` | 1849 | Hard-reset + verify clean state |
| `_materialize_ks40()` | 1869 | Reset primary repo + apply patch unstaged |
| `run_best_of_two_ks40()` | 1904 | Main orchestrator — full best-of-two logic |

### Integration in `solve()` (line 2102)
```python
outcome = run_best_of_two_ks40(config, task, issue)  # KS40 change 1
```
Replaces the old direct `_run_loop(config, task)` call.

### Logic
1. Capture `orig_sha` + verify clean checkout before attempt #1
2. Run attempt #1 via `_run_loop(config, task)` — full KS39 loop, all advantages
3. Measure patch quality; if NOT weak OR remaining < 160s → return attempt #1
4. If weak AND ≥160s remain: `shutil.copytree()` → reset clone → run attempt #2
5. Attempt #2 wall = `max(60s, remaining - 100s)`
6. Only swap if `_patch_key_ks40(b) > _patch_key_ks40(a)` (strictly better)
7. Apply via `git apply`; failure restores attempt #1 via `_materialize_ks40()`
8. `finally` block cleans up tempdir

---

## Change 2 — `_is_weak_patch_ks40()` Quality Detector

**Lines:** 1153–1193 (+helper `_substantive_lines()` at 1142–1151)

```python
def _is_weak_patch_ks40(patch_text, named_files, named_syms, repo_dir, multi_req) -> bool:
```

**Weak conditions (ANY = True):**
- Empty patch (`not patch_text.strip()`)
- Any `.py` file in patch fails `ast.parse()`
- `named_files` non-empty AND no named file touched
- `multi_req=True` AND `_substantive_lines(patch_text) < 2`

`_substantive_lines()` counts added lines (not `+++`) that are stripped len≥3 and don't start with `#`.

---

## Change 3 — `_extract_named_tokens_ks40()` Named Token Extractor

**Lines:** 1120–1137 (+regex constant `_KS40_SYMBOL_RE` at 1123)

```python
def _extract_named_tokens_ks40(issue_text: str) -> (set[str], set[str]):
```

- `named_files`: uses existing `_ISSUE_FILE_RE` pattern (`.py`, `.ts`, `.go`, etc.)
- `named_syms`: `_KS40_SYMBOL_RE = r'\`([A-Za-z_][A-Za-z0-9_]{2,})\`'` (backtick identifiers ≥3 chars)
- Returns `(named_files, named_syms)` as two `set` objects

---

## Change 4 — Enhanced Empty Rescue (8 steps / 60s + partial-credit prompt)

**Constants (lines 104–115):**
```python
_EMPTY_RESCUE_MAX_STEPS = 8    # up from 5 (old constant removed at line 63)
_EMPTY_RESCUE_WALL = 60.0      # up from 30s (renamed from _EMPTY_RESCUE_WALL_SECONDS)
_PARTIAL_CREDIT_NOTE = "..."   # explicit partial-credit framing string
```

**Rescue prompt modification (line 1770):**
```python
+ _PARTIAL_CREDIT_NOTE  # KS40 change 4: explicit partial-credit framing
```
Appended to the return value of `_build_empty_rescue_prompt()`.

**solve() usage (lines 2168, 2176):**
- `max_steps=_EMPTY_RESCUE_MAX_STEPS` (now 8)
- `_EMPTY_RESCUE_WALL` (now 60.0) used in `rescue_wall` calculation

**Note:** The old `_EMPTY_RESCUE_MAX_STEPS = 5` and `_EMPTY_RESCUE_WALL_SECONDS = 30.0` constants were replaced. The `_EMPTY_RESCUE_WALL_SECONDS` reference in `solve()` was updated to `_EMPTY_RESCUE_WALL`.

---

## Change 5 — Hard-Task Detection + Conservative Routing

**Lines:** 567–596 (regex constant + `_is_hard_task_ks40()` + updated `_build_initial_user_prompt()`)

```python
_HARD_TASK_SIGNAL_RE = re.compile(
    r"\b(refactor|rewrite|migrate|restructure|redesign|entire codebase|throughout)\b", re.I
)

def _is_hard_task_ks40(issue_text: str, repo_dir: str) -> bool:
```

**Signals (ANY = True):**
1. No file named in issue text (no `_ISSUE_FILE_RE` matches)
2. Issue text < 80 words AND fewer than 2 backtick symbols
3. Issue text matches `_HARD_TASK_SIGNAL_RE` (refactor/rewrite/migrate/etc.)

**`_build_initial_user_prompt()` update (line 590–596):**
- Added `repo_dir: str = ""` parameter (backward-compatible default)
- If `_is_hard_task_ks40()` returns True, appends `_HARD_TASK_NOTE` to the plan primer
- `solve()` caller updated to pass `repo_dir=repo_path` (line 2101)

**`_HARD_TASK_NOTE` (line 117):**
```
⚠️ CONSERVATIVE STRATEGY: This task has unclear or broad scope.
Make the smallest valid change you can identify with high confidence.
Partial credit beats an empty submission. Focus on ONE clear requirement.
```

---

## Change 6 — Completeness Gate Skip for Substantial Clean Patches

**Location:** `_run_loop()` submission handler, lines 1334–1350

Before firing the completeness gate, the loop now:
1. Collects current patch with `_collect_repo_patch()`
2. Counts added lines with `_line_stats()`
3. If `added_lines > 30` AND `not _has_syntax_errors(repo_dir, patch)` → skips the gate

**`_has_syntax_errors()` helper (line 1197):**
```python
def _has_syntax_errors(repo_dir: str, patch_text: str) -> bool:
```
Iterates touched `.py` files via `_changed_paths()`, attempts `ast.parse()` on each.

**Effect:** A substantial, clean patch (>30 added lines, no syntax errors) skips the completeness nudge and submits immediately. This prevents the completeness gate from holding up a good patch and risking over-engineering.

---

## Deviations from Spec

| Spec | Actual | Reason |
|------|--------|--------|
| `repo_dir` param on `_is_hard_task_ks40` optional | Added as positional 2nd arg | More explicit; called only with repo_dir available |
| `_EMPTY_RESCUE_WALL_SECONDS` renamed `_EMPTY_RESCUE_WALL` | Renamed | Spec says `_EMPTY_RESCUE_WALL = 60.0`; old name was `_EMPTY_RESCUE_WALL_SECONDS` in KS39 |
| Reference to old KS39 header in docstring | Replaced with comment | Python requires `from __future__` immediately after module docstring; a second `"""..."""` block before it is a SyntaxError |

---

## Preserved KS39 Advantages (Untouched)

- `_DEFAULT_CMD_TIMEOUT = 30` (vs king's 15s) ✅
- `_MAX_MESSAGE_CHARS = 180000` (vs king's 90K) ✅
- `_FALLBACK_WALL_CLOCK = 270.0` / `_WALL_CLOCK_RESERVE_SECONDS = 30.0` ✅
- `_NO_PATCH_NUDGE_STEP = 4` ✅
- `_MODEL_ERROR_STREAK_LIMIT = 6` (KS37 congestion resilience) ✅
- `start_new_session=True` in `_execute_command()` (process group kill) ✅
- `SYSTEM_PROMPT` — verbatim king surface, untouched ✅
- `TASK_TEMPLATE` — verbatim king surface, untouched ✅
- Repo preloading (80-item summary + 3 issue files) ✅
- API/route preloading (KS29 fix B) ✅
- C/C++ config awareness (KS34) ✅
- Patch backup + restore (KS32 change C) ✅
- Scratch artifact scrubbing ✅
- History compaction (8-message pinning) ✅

---

## Verification Output

```
COMPILE OK
AST OK
✅ run_best_of_two_ks40
✅ _is_weak_patch_ks40
✅ _extract_named_tokens_ks40
✅ _is_hard_task_ks40
✅ _has_syntax_errors
Lines: 2220
```

---

*Built by Dragon Lord 🐉 | 2026-07-09*

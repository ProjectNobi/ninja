# KING ANALYSIS — SN66 vNEXT
**King file:** `/root/sn66-ninja/king_agent.py` (4595 lines, commit d24c9d3)  
**Baseline:** `/root/sn66-ninja/agent_cl_gpt_v62.py` (4680 lines)  
**Date:** 2026-05-19  
**Scoring context:** LLM-ONLY judge (claude-sonnet-4.6), no cursor_sim (PR#1598)

---

## 1. SYSTEM_PROMPT Full Stats

**Character count:** 12,636 chars  
**Line count:** 162 lines

**Sections in king SYSTEM_PROMPT:**
1. Identity + scoring framing ("smallest correct change a senior maintainer would accept")
2. ABSOLUTE OUTPUT PROTOCOL — `<command>`, `<final>`, `<plan>` format
3. First response format — mandatory `<plan>` block
4. ISSUE CONTRACT — treat issue as a contract, extract all requirements
5. INSPECTION STRATEGY — preloaded snippets first, then focused searches
6. ROOT CAUSE RULE — patch owner of behavior, not downstream symptom
7. SURGICAL EDITING — minimal edits with guarded replacements
8. TESTS AND VERIFICATION — targeted test commands after patching
9. STYLE, COMMENTS, AND PUBLIC API — match adjacent code, preserve comments
10. LANGUAGE-SPECIFIC COMPLETENESS RULES — Java, C/C++, TypeScript/C#, Go/Rust, Dart/Flutter, Multi-file
11. SCOPE DISCIPLINE — explicit "DO NOT change" list
12. SAFETY — no sudo, chmod, deletion, network access

**Vs v62 SYSTEM_PROMPT:** 11,113 chars / 196 lines. v62 is longer due to more explicit COMPLETENESS BEATS MINIMALISM framing, multi-file rule count (3-6 files), and extra surgical editing caveats.

---

## 2. MAX_STEPS and MAX_COMMANDS_PER_RESPONSE

```python
DEFAULT_MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "50"))  # line 71
MAX_COMMANDS_PER_RESPONSE = 25  # line 96
```

**King:** MAX_STEPS=50 (env-configurable), MAX_COMMANDS_PER_RESPONSE=25  
**v62:** Same values — no difference here.

---

## 3. Multi-Shot Refinement Logic

**King has a full multi-shot wrapper: `_solve_with_safety_net` → `_solve_attempt` (attempt 1) → retry.**

### Mechanism:
1. `_solve_with_safety_net` runs `_solve_attempt` as attempt 1
2. If attempt 1 produces **< 3 substantive lines** (`_MULTISHOT_LOW_SIGNAL_THRESHOLD = 3`):
   - AND elapsed < 132s (`_MULTISHOT_MAX_FIRST_ELAPSED`)
   - AND remaining budget > 52s (`_MULTISHOT_MIN_ATTEMPT_RESERVE`)
   - → Revert repo to HEAD, fire attempt 2 with `build_attempt2_bootstrap()`
3. Attempt 2 gets the bootstrap prefix: "prior attempt failed because X, tried file Y — try different approach"
   - Also injects which files attempt 1 touched → steers attempt 2 to different files/layers
4. Winner selection: `_patch_duel_score(patch, issue)` — higher score wins; tie broken by substantive line count
5. If winner is attempt 2, applies attempt 2 patch; if attempt 1 wins, reverts and re-applies attempt 1
6. **Emergency single-shot fallback** (`_solve_emergency_single_shot`): if BOTH attempts produce empty patch + ≥60s remaining → fires 1-shot emergency edit to most likely target file

**Total budget:** `_MULTISHOT_TOTAL_BUDGET = 278.0s`  
Per-attempt inner budget: `WALL_CLOCK_BUDGET_SECONDS = 248.0s`  

**v62:** IDENTICAL multi-shot architecture with same thresholds. Both inherited from same base.

---

## 4. Dynamic Per-Turn Injections

King injects content into messages at runtime based on task state:

### 4a. Initial user prompt augmentation
- **Acceptance criteria checklist** extracted from issue via `_extract_acceptance_criteria()` → appended to initial user message as "address each before `<final>`"
- **Prior attempt summary** (attempt 2 only): bootstrap prefix prepended before initial user content

### 4b. Step 4: Preload strip
- After step 4, bulky preloaded file snippets are replaced with a short breadcrumb (which files were preloaded/modified). Saves ~thousands of chars.

### 4c. Budget pressure prompts (steps 2, 4, no patch)
- `build_budget_pressure_prompt(step)` — "stop exploring, make an edit NOW"

### 4d. Mid-loop hail-mary (DUAL TRIGGER — king-specific)
King has TWO triggers for `build_mid_loop_hail_mary_prompt`:
```python
_hm_time_trigger = elapsed >= _MID_LOOP_HAIL_MARY_BUDGET_FRACTION * wall_clock_budget
_hm_step_trigger = step >= _MID_LOOP_HAIL_MARY_STEP_TRIGGER
if (_hm_time_trigger or _hm_step_trigger) and not patch:
    # fire mid-loop hail-mary
```
→ v62 only has the time trigger. King's step trigger catches fast-inspection loops that haven't edited anything yet.

### 4e. Post-observation nudge (patch exists)
After each observation, if patch exists but not `success`:
- Injects "Next steps: edits → test → `<final>`" hint with suggested test command

### 4f. Verification nudge (step ≥5, patch exists, no recent test)
If patch exists, ≥5 steps elapsed, no verification in last 2 steps: inject targeted test command suggestion.

### Missing vs v62:
- **King LACKS:** `build_soft_nudge_prompt` (30% time, no patch), `build_criteria_self_check_prompt` (80% time, reasoning-only), `build_forced_edit_prompt` (80% time forced edit gate)
- **King HAS:** dual-trigger hail-mary (time OR step count)

---

## 5. Language-Specific Completeness Rules

King's SYSTEM_PROMPT has explicit `LANGUAGE-SPECIFIC COMPLETENESS RULES` section:

| Language | Rule |
|----------|------|
| **Java** | Complete method bodies, cascade all call-site changes, include all imports |
| **C/C++** | Edit both .h AND .cpp, include full signatures + all #includes |
| **TypeScript/C#** | Cascade interface + type changes to ALL implementing classes and function parameters |
| **Go/Rust** | Update every struct field usage, complete Rust lifetime annotations |
| **Dart/Flutter** | Enumerate every `*_screen.dart`, `*_page.dart`, `*_view.dart` as own plan row; mental `git diff --stat` check before `<final>` |
| **Multi-file** | Complete ALL genuinely affected files in same diff |

**v62:** Identical section (same content, same languages). Both inherited from same base.

---

## 6. Task-Type Branching (UPDATE vs BUGFIX vs FEATURE vs REFACTOR)

**King has NO explicit task-type detection or branching.** No code classifies the task type. The same loop runs for all task types.

The SYSTEM_PROMPT handles this implicitly through:
- "ROOT CAUSE RULE" — fix the owner of the behavior
- "SURGICAL EDITING" — minimal edits
- "SCOPE DISCIPLINE" — explicit list of forbidden changes
- No special `UPDATE` or `FEATURE` handling

**v62:** Also NO explicit task-type branching. Same implicit handling.

**⚠️ KEY GAP:** Neither king nor v62 has explicit UPDATE/FEATURE/REFACTOR detection. This is a potential improvement area for vNEXT.

---

## 7. UPDATE Task Handling

**King: NO special UPDATE handling.** UPDATE tasks run through the generic loop.

The king's SYSTEM_PROMPT implicitly helps with UPDATE tasks through:
- "COMPLETENESS vs issue" framing — must satisfy ALL requirements
- Acceptance criteria extraction — bulletted requirements are extracted and re-injected
- Coverage nudge — if issue mentions specific files not touched, nudged

**Implicit weakness:** UPDATE tasks (add a new feature/functionality) require MORE files than BUGFIX. King's "surgical editing" framing biases toward minimal changes, which may underserve UPDATE completeness.

---

## 8. FEATURE Task Handling

**King: NO special FEATURE handling.** Same as UPDATE — runs through generic loop.

Same implicit risks as UPDATE: surgical/minimal framing may under-generate for feature additions that require scaffolding across multiple files.

---

## 9. Forbidden Patterns in SYSTEM_PROMPT

**❌ "Never delete" pattern: NOT PRESENT in king.**

King SYSTEM_PROMPT has SCOPE DISCIPLINE section that says:
```
Do NOT change:
- Whitespace-only, comment-only, or blank-line-only hunks
- Imports not needed by your fix
- [...]
```

But NO rule like "never delete existing functions". In fact, king has a **deletion nudge** that fires when issue requires deletion but patch has no deletions — the opposite of conservative.

**Conservative framing present:**
- "smallest correct change a senior maintainer would accept" (SYSTEM_PROMPT line 2)
- "Change the fewest lines necessary" (SURGICAL EDITING section)
- "Patch the owner of the behavior, not a downstream symptom" (ROOT CAUSE)

**v62:** Identical — no "never delete" pattern, same conservative framing.

---

## 10. Completeness Asymmetry

**King SYSTEM_PROMPT does NOT have explicit "under-editing costs more than over-editing" statement.**

King mentions: "The LLM judge penalizes incomplete solutions" in the initial user prompt (not SYSTEM_PROMPT).

**v62 SYSTEM_PROMPT has explicit asymmetry:**
```
Under-editing (missing a cascade file) is penalized MORE than slight over-editing. When in doubt, include the file.
```
And: "COMPLETENESS BEATS MINIMALISM. Missing files/requirements costs far more than extra thorough edits."

**⚠️ KEY FINDING:** King relies on "surgical editing" framing without the explicit completeness asymmetry that v62 has. Under LLM-only scoring where completeness is heavily weighted, v62's explicit asymmetry may be advantageous.

---

## 11. Key Helper Methods

### Multi-shot / Architecture
- `_solve_with_safety_net(**kwargs)` — outer multi-shot driver, calls `_solve_attempt` twice if needed
- `_solve_attempt(**kwargs)` — inner agent loop (single attempt)
- `_solve_emergency_single_shot(**kwargs)` — 1-shot emergency rescue for empty-patch cases
- `_multishot_capture_head` / `_multishot_revert` — git HEAD capture + hard reset for attempt 2

### Context building
- `build_preloaded_context(repo, issue)` — ranks and preloads likely relevant files
- `_rank_context_files(repo, issue)` — scores files by issue term overlap
- `_augment_with_directory_siblings`, `_augment_with_integration_partners` — context broadening
- `_augment_with_test_partners(files, tracked)` — find companion test files
- `_recent_commit_examples(repo)` — inject recent small-diff commits as style anchors
- `_strip_preloaded_section` — strips bulky preloads at step 4

### Refinement gates
- `maybe_queue_refinement(assistant_text)` — 7-gate pipeline: syntax→test→deletion→criteria→coverage→polish→self-check
- `build_deletion_nudge_prompt` — fires when issue requires removals but patch has none
- `build_coverage_nudge_prompt` — fires when issue-mentioned paths are untouched
- `build_criteria_nudge_prompt` — fires when acceptance criteria look unaddressed
- `build_self_check_prompt` — final pass: show diff + ask "did you cover everything?"
- `build_mid_loop_hail_mary_prompt` — emergency when no patch at time/step threshold

### Patch quality
- `_patch_duel_score(patch, issue)` — scores patch quality for winner selection
- `_patch_ship_blockers(patch, issue)` — identifies blockers before declaring success
- `_strip_low_signal_hunks` — removes whitespace/comment-only diff hunks
- `_strip_lockfile_diffs_unless_mentioned` — post-process: remove lockfile diffs
- `_extract_acceptance_criteria(issue_text)` — parse issue bullets as criteria

---

## 12. Architecture Summary (200 words)

King is a sophisticated multi-shot SWE agent built for the LLM judge scoring paradigm (correctness + completeness + reference similarity). Its core architecture: a safety-netted outer loop runs up to 2 inner solve attempts. If attempt 1 produces fewer than 3 substantive diff lines, it reverts the repo and fires attempt 2 with a "try different approach" bootstrap prefix listing what attempt 1 touched. Winner is selected by a `_patch_duel_score` heuristic. An emergency 1-shot fallback handles the guaranteed-zero empty-patch case.

The inner agent loop is tightly managed: preloaded context is stripped after step 4 to save tokens; a mid-loop hail-mary fires on EITHER time elapsed OR step count (dual-trigger, king-specific); budget pressure nudges fire at steps 2 and 4. The 7-gate `maybe_queue_refinement` pipeline (syntax→test→deletion→criteria→coverage→polish→self-check) catches the most common failure modes before the agent exits.

The SYSTEM_PROMPT is precisely engineered around minimalism + correctness: ROOT CAUSE RULE, SURGICAL EDITING, SCOPE DISCIPLINE, language-specific completeness rules for Java/TS/Flutter/Go/Rust. However, king lacks explicit "under-editing costs more than over-editing" asymmetry (v62 has this), lacks soft-nudge and forced-edit at 80% wall-clock (v62 has these), and has no task-type branching for UPDATE vs FEATURE vs REFACTOR.

---

## KEY GAPS vs vNEXT OPPORTUNITIES

| Gap | King | v62 | vNEXT opportunity |
|-----|------|-----|-------------------|
| Completeness asymmetry | ❌ Implicit | ✅ Explicit | Add to SYSTEM_PROMPT |
| Soft nudge (30% time, no patch) | ❌ | ✅ | Add soft nudge |
| Forced edit at 80% wall-clock | ❌ | ✅ | Add forced edit gate |
| Criteria self-check at 80% | ❌ | ✅ | Add criteria self-check |
| Static analysis gate | ❌ | ✅ | Add after syntax gate |
| Task-type branching (UPDATE/FEATURE/REFACTOR) | ❌ | ❌ | NEW — implement |
| UPDATE-specific completeness rules | ❌ | ❌ | NEW — implement |
| Dual trigger hail-mary | ✅ | ❌ | Keep |
| Multi-shot retry | ✅ | ✅ | Same |
| Deletion nudge | ✅ | ✅ | Same |

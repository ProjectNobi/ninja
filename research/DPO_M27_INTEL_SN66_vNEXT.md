# DPO + M2.7 Intel — SN66 vNEXT (2026-05-18)

## 2a: What gpt-5.4 Rewards (DPO Analysis)

### UPDATE Tasks (top 5 reward patterns)

1. **"complete" / "more complete"** — 258 occurrences
   - Verbatim: "Solution B is more complete and directly addresses..."
   - Verbatim: "Solution A appears incomplete... Solution B at least..."
   - The judge consistently rewards patches that implement ALL stated acceptance criteria

2. **"correctly implements" / "directly implements"** — 102 occurrences
   - Verbatim: "Solution B directly implements the required [X] logic"
   - Verbatim: "Solution A correctly adds a root handler in the existing Gin router"
   - The judge rewards code that hits the exact API/file being used in the codebase

3. **"matches" / "better matches"** — 67 occurrences
   - Verbatim: "Solution B better matches the requirement to preserve existing [X] by month"
   - Verbatim: "Solution A matches the apparent Go/Gin codebase"
   - **Critical**: Codebase matching is a top-3 factor — wrong stack/framework = automatic loss

4. **"end-to-end"** — 21 occurrences
   - Verbatim: "Solution A addresses the core OAuth flow end-to-end"
   - Verbatim: "addresses both the [X] and [Y] requirements end-to-end"
   - Winning patches demonstrate full pipeline: data model → service → API → integration

5. **"preserves" / "maintains"** — 18 occurrences
   - Verbatim: "preserves existing slab data by matching slabs to selected months"
   - Verbatim: "preserves current API routes"
   - Verbatim: "maintains backward compatibility"

### UPDATE Tasks (top 5 penalty patterns)

1. **"incomplete" / "appears incomplete"** — 293 occurrences (most common failure mode)
   - Verbatim: "Solution A is essentially incomplete, showing only import additions..."
   - Verbatim: "Solution B appears incomplete/truncated"
   - **#1 killer**: Partial implementations that don't show the full acceptance criteria

2. **"partial" / "truncated"** — 107 occurrences
   - Verbatim: "the patch is incomplete/truncated"
   - Verbatim: "appears partial"
   - Diff doesn't show complete implementation

3. **"different stack" / "different codebase" / "different framework"** — 15 occurrences
   - Verbatim: "Solution B targets a different stack and file layout entirely"
   - Verbatim: "Solution A appears to target a different Python/FastAPI codebase"
   - **Catastrophic**: Targeting wrong technology stack = automatic rejection

4. **"does not show" / "does not demonstrate"** — 72 occurrences
   - Verbatim: "does not show the actual [X] logic"
   - Verbatim: "does not demonstrate the required integration"
   - Missing evidence of behavior in the diff

5. **"incorrect" / "wrong" / "less likely"** — 56 occurrences
   - Verbatim: "appears inconsistent with the described API"
   - Verbatim: "is less likely to integrate or satisfy the task"

### FEATURE Tasks (top 3 reward patterns)

1. **"end-to-end" flow implementation** — Core feature from API to UI
   - Verbatim: "Patch B addresses the core OAuth flow end-to-end: it adds a reusable Google button component, initiates Google sign-in, and implements the callback route"

2. **"addresses explicit acceptance criteria"** — Checking off requirements
   - Verbatim: "it at least touches two explicit acceptance criteria from the issue: exposing a settings entry for rules and adding a transaction-detail flow"

3. **"correct file targeting"** — Modifying the right files
   - Verbatim: "Patch A is better because it updates the actual validator with tests and explicitly preserves rejection of invalid formats"

### FEATURE Tasks (top 3 penalty patterns)

1. **"incomplete/partial"** — Missing full feature implementation
   
2. **"truncated diff"** — Can't verify end-to-end behavior

3. **"wrong stack/file"** — Modifying incorrect files

### BUGFIX Tasks (top 3 reward patterns)

1. **"root cause fix"** — Fixing the actual problem, not symptoms
   - Verbatim: "Patch B addresses the core root-cause fix for instant reloads"

2. **"addresses acceptance criteria"** — Meeting all stated requirements

3. **"correct API/data structures"** — Using the right interfaces
   - Verbatim: "directly fixes the reported root cause at the call site by ensuring both VM binding functions always receive non-NULL arrays"

### BUGFIX Tasks (top 3 penalty patterns)

1. **"incomplete"** — Not showing full fix
   
2. **"different file paths than issue context"** — Wrong files

3. **"introduces undeclared/likely nonexistent symbols"** — References non-existent code

### Patch Size Analysis

| Metric | Value |
|--------|-------|
| Avg CHOSEN (winner) lines | 237.9 |
| Avg REJECTED (loser) lines | 226.7 |
| Winner bigger by | +11.1 lines (+4.9%) |
| Winner bigger | 51.7% of time |
| Winner smaller | 47.7% of time |
| Winner equal | 0.7% of time |

**Finding**: Size is NOT the primary factor. Winner is bigger only 51.7% of the time. Completeness and correctness matter more than raw patch size.

### Universal Winner Pattern

The single most common phrase in winning rationales:

**"better matches"** (16 occurrences) / **"directly implements"** (13 occurrences)

Combined interpretation: **The winning patch TARGETS THE CORRECT CODEBASE and DIRECTLY IMPLEMENTS the complete requirement.**

Key insight: 15% of losing patches (15/100 sampled) fail due to "different stack" or "different codebase" targeting. This is the #1 preventable failure.

---

## 2b: M2.7 Blind Spots

### Under-edit vs Over-edit

| Archetype | M2.7 Avg Lines | Reference Avg Lines | Ratio |
|-----------|----------------|---------------------|-------|
| FEATURE_BUILD | 349.2 | 722.7 | **-51.7%** |
| MIGRATION | 310.4 | 677.4 | **-54.2%** |
| BUG_FIX | 239.6 | 480.8 | **-50.2%** |
| REFACTOR | 296.1 | 479.0 | **-38.2%** |
| **OVERALL** | **334.1** | **677.0** | **-50.7%** |

**M2.7 under-edits by ~50%** compared to reference patches across all archetypes.

40% of M2.7 tasks under-edit by more than 30%:
- FEATURE_BUILD: Some tasks -70% to -83% vs reference
- MIGRATION: Worst case -83% (339 lines vs 20,032 reference)
- REFACTOR: -70% (467 lines vs 1,532 reference)

### What M2.7 Consistently Misses

1. **Complete acceptance criteria coverage**
   - M2.7 adds partial implementation but omits edge cases
   - Reference: 722 lines for FEATURE_BUILD, M2.7: 349 lines
   - Example: r2_05724 — M2.7 added 25 lines, reference added 146 (+483% more)

2. **End-to-end integration wiring**
   - M2.7 adds new code but doesn't wire into existing lifecycle
   - Reference patches show: service layer → API layer → UI integration → tests
   - M2.7 often stops at service layer

3. **Full edge case handling**
   - M2.7 implements happy path, misses error handling, fallbacks, defaults
   - Reference: comprehensive error handling, validation, edge cases
   - M2.7: minimal viable implementation only

4. **Cross-file ripple effects**
   - M2.7 modifies one file but misses dependent files
   - Reference often touches 3-5 files for complete feature
   - M2.7 tends to stay in single file

### SYSTEM_PROMPT Compensations Required

Based on the gap analysis, vNEXT SYSTEM_PROMPT MUST include:

1. **Completeness Check Rule**: 
   ```
   Before submitting: verify you've addressed EVERY acceptance criterion listed in the task.
   List each criterion and confirm your patch addresses it.
   ```

2. **Codebase Match Rule**:
   ```
   CRITICAL: Your patch MUST target the EXACT stack/framework shown in the task.
   If the task shows Go/Gin, do NOT add Python/FastAPI. If the task shows React, do NOT add Vue.
   Wrong stack = automatic rejection regardless of code quality.
   ```

3. **End-to-End Wiring Rule**:
   ```
   For FEATURE tasks: your patch must show the full pipeline: data model → service → API → integration.
   Simply adding a function is NOT sufficient. Wire it into the existing flow.
   ```

4. **Multi-file Touch Rule**:
   ```
   When modifying a feature, check ALL files that depend on it (API routes, UI components, tests, configs).
   If the reference patch touches 3+ files, your patch likely needs to as well.
   ```

5. **Under-editing Detection**:
   ```
   If your patch is <50% of the expected size based on task complexity, you're under-editing.
   Add missing edge cases, error handling, and integration points.
   ```

---

## Summary: Top 7 Actionable Rules for vNEXT SYSTEM_PROMPT

1. **MATCH THE CODEBASE** — Use the exact framework/stack shown in the task. Wrong technology = instant loss.

2. **COMPLETE ALL ACCEPTANCE CRITERIA** — List each criterion and verify your patch addresses it. Incomplete = #1 failure mode.

3. **END-TO-END WIRE** — Show the full pipeline: data → service → API → UI → tests. Partial implementations lose.

4. **PRESERVE EXISTING BEHAVIOR** — Don't break what's already working. "Preserves", "maintains", "doesn't interfere" are top winner patterns.

5. **TARGET THE ROOT CAUSE** — For BUGFIX, fix the actual problem, not symptoms. Reference the exact API/call site.

6. **MULTI-FILE COMPLETENESS** — Check dependent files. If reference touches 3+ files, you likely need to.

7. **WHEN IN DOUBT, ADD MORE** — M2.7 under-edits by 50%. Slight over-edit beats under-edit. The judge penalizes missing more than extra lines.

---

## Evidence Sources

- DPO analysis: `/root/sn66-ninja/training_data/update_task_dpo_pairs.jsonl` (first 300 records)
- Full matrix DPO: `/root/sn66-ninja/training_data/full_matrix_dpo_pairs.jsonl` (first 150 records)
- M2.7 gold patches: `/root/sn66-ninja/training_data/gold_patches/gold_patches_minimax_minimax-m2_7.jsonl` (first 500 records)
- Record structure confirmed: `task_id`, `archetype`, `model`, `llm_patch`, `reference_patch`, `n_added_llm`, `n_added_ref`, `elapsed_s`

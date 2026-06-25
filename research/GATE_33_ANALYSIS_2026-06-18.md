# Gate-33 Analysis — Next33 vs King hashirama
Date: 2026-06-18 06:41 UTC
Agent: agent_cl_gpt_Next33.py (2506 lines)
King: king_agent.py (1262 lines, SHA 53bca97c)
Verdict: NOT COMPETITIVE ❌ (60% = 6W-4L, threshold 80%)

---

## Full Round Breakdown

| # | Type       | Lang       | Us    | King  | Result | Notes                                      |
|---|------------|------------|-------|-------|--------|--------------------------------------------|
| 1 | BUGFIX     | C/C++      | 0.280 | 0.630 | ❌ LOSS | C++ Password Manager — king dominated, 0.350 margin |
| 2 | BUGFIX     | Python     | 0.620 | 0.420 | ✅ WIN  | Intent Detection API — solid win |
| 3 | BUGFIX     | TypeScript | 0.520 | 0.180 | ✅ WIN  | Node Styling Refactor — dominated |
| 4 | API/ROUTE  | Python     | 0.450 | 0.100 | ✅ WIN  | Repository Analysis — dominated |
| 5 | API/ROUTE  | PHP        | 0.300 | 0.440 | ❌ LOSS | Password Reset PHP — king 0.140 margin |
| 6 | BUGFIX     | Go         | 0.150 | 0.200 | ❌ LOSS | P2P SkyFS Sync — tight loss, small files |
| 7 | API/ROUTE  | JavaScript | 0.330 | 0.420 | ❌ LOSS | Pregnancy/Lactation JS chat tab — king 0.090 margin |
| 8 | BUGFIX     | TypeScript | 0.450 | 0.000 | ✅ WIN  | HTTP Server DI — T8 fix working |
| 9 | FEATURE    | TypeScript | 0.850 | 0.000 | ✅ WIN  | Map Zoom Speed — dominated |
|10 | BUGFIX     | Python     | 0.270 | 0.140 | ✅ WIN  | LoRA Publish Flow — won |

## Aggregate Stats
- Decisive win rate: 60% (6W-4L) — need 80%+ for gate-10 pass
- Cursor-sim avg: ours 0.162 vs king 0.083 — we produce more reference-similar patches
- Win rate by type: BUGFIX 4/6 (66.7%), API/ROUTE 1/3 (33.3%), FEATURE 1/1 (100%)

---

## Loss Root Cause Analysis

### LOSS T1 — C++ Password Manager (0.280 vs 0.630)
- **King margin: +0.350** — our largest loss
- Our cursor-sim 0.157 vs king 0.211 → king also more reference-similar
- This is NOT a polish regression (scoring gap is large, not subtle)
- King likely understands the C++ pattern better → real implementation gap
- Language: C/C++ — we may lack C++ specific strategies
- Low output: ours 0.280 suggests partial or incorrect patch

### LOSS T5 — PHP Password Reset (0.300 vs 0.440)
- **King margin: +0.140**
- Our cursor-sim 0.135 vs king 0.181 → king more reference-similar
- PHP backend routes — multi-file backend API integration pattern
- We score 0.300 (functional but incomplete?) vs king 0.440
- PHP is a less-common language in our training, possibly undertrained strategies

### LOSS T6 — Go P2P SkyFS (0.150 vs 0.200)
- **King margin: +0.050** — tightest loss
- Our cursor-sim 0.048 vs king 0.054 — very close, slightly favors king
- Large-repo Go task (11 files!) — our is_large_repo_task should fire
- Very low scores both sides (0.150 vs 0.200) → this is a hard task
- Possibly timeout/budget issue on complex 11-file Go task
- The go-integration test file + 10 other files = complex dependency mapping

### LOSS T7 — JavaScript React Tab (0.330 vs 0.420)
- **King margin: +0.090**
- Our cursor-sim 0.121 vs king 0.055 → WE are more reference-similar yet still LOST
- Judge penalized us despite more similar patch — suggests different quality axis
- This is the same JS task type that's been problematic in previous gates
- Next33 added a JS chat/AI chat hint that helped (330 vs 300 baseline?) but not enough

---

## Cross-Gate Pattern Analysis (Across Next30–Next33)

### Persistent weakness: API/ROUTE tasks
- Gate-33: API/ROUTE 1/3 (33.3%)
- Gate-32: API/ROUTE 2/3 (before gate-33, mixed)
- Pattern: multi-file API integration tasks (PHP routes, JS React components) consistently lose
- Root cause: king appears to have a more systematic approach to API/route integration

### C++ losses
- T1 gate-33 (C++ Password Manager): 0.280 vs 0.630 — significant gap
- King substantially better on C++ systems code
- No C++ specific strategies in our agent

### Go large-repo tasks
- T6 gate-33 (11 files Go): 0.150 vs 0.200 — marginal loss but poor absolute score
- Both agents struggle; king slightly better
- Our large-repo detection may not help enough for Go

### What IS working
- TypeScript: strong (DI fix working, feature tasks dominate)
- Python BUGFIX: good
- FEATURE tasks: 100% win rate
- _CONTAINER_DI_RE hint: still paying off (T8: 0.450 vs 0.000)
- _polish_worth_adopting guard: preventing polish regression (no T1/T2 regression from Next31)

---

## SN66 Duel 007034 Context (from ninja66.ai)
- ProjectNobi-v33 submitted as challenger to king hashirama
- Duel result: LOST (live on-chain)
- King has been dominant, ~0.950 peak scores

---

## Hypotheses for Next34

### H1 — C++ Strategy Gap (HIGH PRIORITY — largest margin loss T1)
The king likely has C++ specific strategies: understand pointer/memory management patterns, 
recognize common C++ bug classes (buffer overflow, RAII, null ptr, object lifecycle).
Add a C++ hint in _integration_hints() that fires when language=C/C++ and it's a BUGFIX:
"For C++ bugfixes: check memory management (RAII, unique_ptr, shared_ptr), null/bounds checks,
class lifecycle (constructor/destructor/copy). Read the header files first."

### H2 — API/ROUTE Multi-Step Strategy (MEDIUM — 33% win rate)
For API/ROUTE tasks, the king appears to implement more completely in the first pass.
Our agent may be reading too much before implementing.
For multi-file API route tasks: add a "route integration" hint that says:
"Implement the route handler first (model, validation, response), then wire middleware/auth,
then update tests. Don't read all files before starting — implement the core route in step 1."

### H3 — PHP Backend Strategy (MEDIUM — T5 loss)
PHP password reset is a standard pattern (token generation, email dispatch, DB update).
When language=PHP and route/backend: 
"Follow Laravel/Slim/vanilla PHP patterns: check Request → validate → generate token → 
store hash → dispatch mail → return response. Implement all steps in one pass."

### H4 — Go Large-Repo Timeout (LOW — T6 tight loss)
T6 had 11 files and very low absolute scores (0.150 vs 0.200).
Both agents may be timing out or truncating. If Go + >8 files, focus on the primary 
goroutine/channel/sync pattern rather than touching all 11 files.

---

## Recommended Changes for Next34 (strictly surgical)

**CHANGE 1 (C++ BUGFIX hint — closes T1 gap)**
In `_integration_hints()`, add: when lang contains 'c' or 'cpp' (matched via file extensions 
`.cpp`, `.cc`, `.c`, `.h`, `.hpp`) AND task type is BUGFIX:
→ inject "C++ bug hint: check memory lifecycle (RAII, raw ptrs→smart ptrs, destructor), 
null/bounds guards, const-correctness, and header-declared vs defined discrepancies. 
Read header files first."

**CHANGE 2 (API/ROUTE first-action hint — closes T5, T7 gap)**
In `build_initial_user_prompt()`, for API/ROUTE type tasks:
→ tighten the "implement first" bias: 
"Start with the primary route/endpoint handler — write the core logic first, then wire 
supporting files. Do not read more than 2 files before making your first edit."

**CHANGE 3 (Go large-repo focus — closes T6 gap)**
In `_integration_hints()`, when language is Go AND file count > 8:
→ inject "Large Go repo: identify the primary goroutine/sync/channel that owns this feature.
Focus changes on that package only. Avoid touching test/integration files unless the fix
clearly requires it."

---

## Next34 build brief for Opus

Build agent_cl_gpt_Next34.py from agent_cl_gpt_Next33.py with EXACTLY THREE surgical changes:
1. C++ BUGFIX hint in _integration_hints()
2. API/ROUTE first-action tightening in build_initial_user_prompt()  
3. Go large-repo focus in _integration_hints()

DO NOT change:
- _build_polish_task (king-byte-identical, verified SHA 53bca97c)
- _polish_worth_adopting guard (Next33 fix, working)
- _CONTAINER_DI_RE (T8 fix, still paying off)
- render_observation (king-identical <=3 ONLY rule)
- sampling params
- _sanitize_patch
- stdlib only — zero new imports

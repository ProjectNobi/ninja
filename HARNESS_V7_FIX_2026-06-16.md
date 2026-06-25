# validator_harness_v7.py — Security Fix Report (2026-06-16)

**Auditor:** Opus 4.8 (subagent)
**Scope:** `validator_harness_v7.py` only (+ this report)
**Severity:** HIGH — live API key exposure in process table

---

## 1. What Was Found

### CRITICAL — OpenRouter API key exposed via subprocess argv (FIXED)
`_RUNNER_TEMPLATE` baked the key into the `python3 -c "<script>"` string passed
to `subprocess.run([sys.executable, "-c", script], ...)`. The full `sk-or-v1-...`
key was therefore visible in `ps aux` and `/proc/<pid>/cmdline` for **every** agent
subprocess.

- `validator_harness_v7.py:722` (old) — `api_key = {api_key!r}` inside the template
- `validator_harness_v7.py:782` (old) — `api_key=api_key` passed to `.format(...)`
- `validator_harness_v7.py:787` (old) — `subprocess.run(..., text=True, timeout=timeout)` with **no** `env=`

Blast radius: gate runs spawn 2 agents × 30 tasks = up to 60 subprocesses, each
leaking the key for its full lifetime. Live `ps aux` previously captured
`api_key = 'sk-or-v1-...a700'` in full. **`challenger_api_key` flowed through the
same `run_agent()` path and was equally exposed.**

### No other argv secret leaks found
- The only other argv-based subprocesses are `git` calls
  (`validator_harness_v7.py:610, 639–667`) — no secrets in their arguments.
- The LLM judge (`_judge_api_call`, `validator_harness_v7.py:822`) sends the key in
  an HTTP `Authorization: Bearer` header (`:846`) — never on a command line. Safe.
- `api_base` is non-secret; left as a template literal (no exposure concern).

### Minor / not changed (out of scope, low risk)
- `SECRETS_FILE = "/root/.secrets/api_keys.env"` hardcoded path (`:94`) — acceptable;
  matches fleet convention.
- No world-readable temp files for secrets observed; git temp dirs contain only repo
  state, not keys.

---

## 2. What Was Changed

Minimal, signature-preserving edits (no public API change):

1. **`_RUNNER_TEMPLATE`** (now `:715`–`:723`):
   - Added `import os as _os`
   - Replaced `api_key = {api_key!r}` → `api_key = _os.environ.get("_HARNESS_API_KEY", "")`

2. **`run_agent()`** (now `:777`–`:792`):
   - Removed `api_key=api_key` from the `_RUNNER_TEMPLATE.format(...)` call
   - Added `runner_env = {**os.environ, "_HARNESS_API_KEY": api_key}`
   - Passed `env=runner_env` to `subprocess.run(...)`
   - Added a `# SECURITY:` comment documenting the rationale

The key is now delivered through the child's environment (`/proc/<pid>/environ`,
mode 0400, owner-only) instead of its argv. `challenger_api_key` is automatically
covered because it is passed in as `api_key=c_key` to the same `run_agent()`.

---

## 3. Test Results

- **Syntax:** `ast.parse(...)` → `syntax OK`
- **Module import:** `spec.loader.exec_module` → `import OK; run_agent present: True`
- **Template placeholders after fix:** `['agent_path','api_base','issue','max_steps','model','repo_path']` — `api_key` correctly removed (no `.format()` KeyError risk)
- **Env round-trip:** child read `_HARNESS_API_KEY` → `got key: test-key...` ✅
- **ps / cmdline leak check (secret built at runtime):**
  - `secret in child argv? False` ✅ (leak closed)
  - `secret in child environ (root-only)? True` (expected, private)
  - Note: the task's literal `ps`-grep test reports a *false* FAIL because the secret
    string lives in the **test runner's own** `python3 -c` argv, not the child's.
    Verified via `/proc/<child_pid>/cmdline` that the real subprocess argv is clean.

A full gate test was **not** run (per task constraints — too slow).

---

## 4. Remaining Issues (flagged, not fixed — out of scope)
- None security-critical. The hardcoded `SECRETS_FILE` path is intentional fleet
  convention. No further argv secret exposure exists in this file.

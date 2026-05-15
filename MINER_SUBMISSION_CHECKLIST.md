# SN66 Ninja Miner Submission Checklist
*Updated: 2026-05-15 05:57 UTC | T68Bot*

## 👑 CURRENT KING (T68 internal — update when king changes)
| Field | Value |
|-------|-------|
| King | **5FGuXw2aEJCu** (private submission) |
| PR | N/A — private submission |
| SHA | `627b16d9ffdbe805` |
| Lines | 4,247 |
| Local file | `king_agent.py` ✅ updated 2026-05-15 |
| Confirmed | 2026-05-15 14:51 UTC — Arbos promotion commit |
| Architecture | Multishot + `_find_test_partner_by_grep()` + budget deferral + enhanced attempt-2 bootstrap |
| Previous king | adamninja PR#1551 (4,106L) → archive: `agents_archive/king_agent_adamninja_pr1551_backup.py` |

---

## 🔥 CURRENT BEST CHALLENGER — agent_cl_gpt_v49.py
| Field | Value |
|-------|-------|
| Version | **CL-GPT-v49** |
| File | `/root/sn66-ninja/agent_cl_gpt_v49.py` |
| Archive | `/root/sn66-ninja/agents_archive/agent_cl_gpt_v49.py` |
| Lines | 5,094 (+303 vs v41 base) |
| Built | 2026-05-15 by Opus 4.7 |
| Audit | ✅ CLEAN — 0 critical issues, all 8 rules pass |
| Gate test | Running — 25 tasks x 3 seeds vs new king, GPT-5.4 judge |
| Gate threshold | >=70% decisive WR — ask James for submission approval |
| Base | v41 (59.5% vs adamninja) |
| Estimated WR | 60-65% conservative, 65-70% optimistic vs new king |

### v49 New Features vs v41
1. _find_test_partner_by_grep() — grep fallback test discovery (from new king)
2. _last_assistant_named_target() — budget deferral (from new king)
3. Enhanced build_attempt2_bootstrap() — file hints for attempt 2 (from new king)
4. Needle-based preloading — windowed large-file truncation fix
5. Wiring gap gate — orphan presentation file detection (king lacks this)

---

## 🚨 SUBMISSION FORMAT CHANGED (2026-05-14)
**The OLD PR-based flow is DEAD. No more PRs, no CI gates, no on-chain commits.**
**Use the private submission API (`scripts/submit_private_submission.py`) instead.**

---

Subnet 66 miners submit exactly one file, `agent.py`, to the private submission
API. The validator verifies the signing hotkey, runs private gates, stores the
accepted bundle, and queues accepted challengers from the private submission
ledger.

There is no miner pull request flow and no on-chain commitment flow for ninja
submissions.

## Quick Path

```bash
python3 -m py_compile agent.py
python3 -c "from agent import solve; print('Import OK')"

./scripts/submit_private_submission.py \
  --wallet-name <wallet-name> \
  --wallet-hotkey <wallet-hotkey-name> \
  --hotkey <miner-hotkey-ss58>
```

The default endpoint is:

```text
https://ninja66.ai/api/submissions
```

For local testing, pass `--api-url http://127.0.0.1:8066/api/submissions`.

## Before You Submit

- [ ] Your hotkey is registered on Subnet 66.
- [ ] This registration has not already produced an accepted private submission.
- [ ] `agent.py` is 5 MB or smaller.
- [ ] `agent.py` compiles with `python3 -m py_compile agent.py`.
- [ ] `from agent import solve` imports cleanly.
- [ ] `solve(repo_path, issue, model, api_base, api_key)` still accepts the
  validator-owned parameters in that order.
- [ ] `solve(...)` returns a dict with `patch`, `logs`, `steps`, `cost`, and
  `success`.
- [ ] New logic uses Python standard library only.
- [ ] No hardcoded API keys, bearer tokens, provider URLs, or wallet material.
- [ ] No hardcoded model names. Use the `model` argument supplied by the
  validator.
- [ ] No sampling controls such as `temperature`, `top_p`, `top_k`, `seed`,
  penalties, `logit_bias`, or `logprobs`.
- [ ] No validator-detection, hidden-test sniffing, telemetry, or external
  network calls outside the validator-provided LLM endpoint.

## Submit

Run:

```bash
./scripts/submit_private_submission.py \
  --wallet-name <wallet-name> \
  --wallet-hotkey <wallet-hotkey-name> \
  --hotkey <miner-hotkey-ss58>
```

The helper reads `agent.py`, derives a submission id, signs this payload with
your wallet hotkey, and posts a multipart request to the API:

```text
tau-private-submission-v1:<hotkey>:<submission-id>:<sha256-of-agent.py>
```

Use `--dry-run` to print the request summary without sending it.

## API Result

If the API rejects the submission, the helper prints the JSON response and exits
nonzero. Fix the issue and submit again only if your registration is still
eligible.

If the API accepts the submission, the response includes:

```text
private-submission:<submission-id>:<sha256-of-agent.py>
```

Accepted public metadata is published at:

```text
https://ninja66.ai/api/submissions
```

That public payload does not expose your submitted `agent.py` contents or
signature.

## Validator Gates

The API rejects cheap invalid requests first, then runs heavier checks:

- `Signature Gate` validates the signed hotkey payload.
- `Registration Gate` confirms the hotkey is currently registered and not spent
  for this registration.
- `Agent Smoke` compiles/imports `agent.py` and checks basic contract shape.
- `Submission Scope Guard` rejects forbidden files, provider bypasses, sampling
  controls, secret usage, and contract breaks.
- `OpenRouter Submission Judge` uses the same gatekeeping judge prompt as the
  legacy ninja CI, with `anthropic/claude-opus-4.7`, temperature `0`, and medium
  reasoning effort.

## Common Rejection Reasons

| Mistake | Result |
|---|---|
| Invalid signature or wrong wallet hotkey | Quick API rejection |
| Hotkey is not registered | Rejected before smoke/judge checks |
| Hotkey already accepted for this registration | Rejected before smoke/judge checks |
| `agent.py` exceeds 5 MB | Rejected before validation |
| Syntax/import error | `Agent Smoke` fails |
| Changed `solve(...)` contract | Scope guard or smoke fails |
| Hardcoded model/provider/API key | Scope guard fails |
| Sampling parameters in LLM calls | Scope guard fails |
| Cosmetic or copied agent change | Submission judge fails |
| External network calls or telemetry | Scope guard or judge fails |

## Local Checks

```bash
python3 -m py_compile agent.py
python3 -c "from agent import solve; print('Import OK')"
python3 - <<'PY'
import inspect
from agent import solve

params = list(inspect.signature(solve).parameters)
expected = ["repo_path", "issue", "model", "api_base", "api_key"]
assert params[: len(expected)] == expected, params
print("Signature OK:", params)
PY
rg -n "temperature|top_p|top_k|seed|presence_penalty|frequency_penalty|logit_bias|logprobs" agent.py
rg -n "sk-|Bearer |api_key\\s*=\\s*['\\\"]|OPENROUTER|OPENAI_API_KEY|ANTHROPIC" agent.py
```

Review any `rg` matches carefully before submitting. Some matches can be benign
when they refer to validator-supplied parameters, but hardcoded secrets,
providers, models, or sampling controls are disqualifying.

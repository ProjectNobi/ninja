#!/usr/bin/env bash
# sync_king.sh — Fetch the current SN66 king from ninja66.ai dashboard + GitHub
# Usage: bash scripts/sync_king.sh   (works from ANY directory)
# Always run this BEFORE any gate test or pipeline task (L-SN66-KING-SYNC-PIPELINE-1)
set -euo pipefail

# ── Absolute paths (safe from any working directory) ──────────────────────────
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
KING_FILE="$REPO_ROOT/king_agent.py"
SHA_FILE="$REPO_ROOT/.king_sha"
DASHBOARD_URL="https://ninja66.ai/dashboard.json"
GITHUB_API="https://api.github.com/repos"
MIN_LINES=100   # new multi-file king entrypoint is ~165L; 100 is safe minimum
STALE_DAYS=7     # warn if dashboard updated_at is older than this

# ── Temp file + cleanup trap ───────────────────────────────────────────────────
TMP_KING=$(mktemp /tmp/sync_king_XXXXXX.py)
trap 'rm -f "$TMP_KING"' EXIT

# ── Step 1: Fetch dashboard ────────────────────────────────────────────────────
echo "🔍 Fetching king info from dashboard..."
KING_JSON=$(curl -sf --max-time 30 "$DASHBOARD_URL") || {
    echo "❌ Failed to fetch dashboard.json (timeout or network error)"
    exit 1
}

# ── Step 2: Extract SHA + repo + updated_at from dashboard ────────────────────
read -r LIVE_SHA RUNTIME_REPO DASHBOARD_UPDATED_AT < <(echo "$KING_JSON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
k = d.get('current_king', {})
sha  = (k.get('runtime_commit_sha') or k.get('commit_sha') or '').strip()
repo = (k.get('runtime_repo_full_name') or 'unarbos/ninja').strip()
updated_at = d.get('updated_at', '').strip()
if not sha:
    sys.stderr.write('ERROR: no SHA in dashboard response\n')
    sys.exit(1)
print(sha, repo, updated_at)
") || {
    echo "❌ Could not parse king SHA from dashboard.json"
    exit 1
}

if [[ -z "$LIVE_SHA" ]]; then
    echo "❌ Empty SHA returned from dashboard"
    exit 1
fi

# ── Step 2b: Check dashboard freshness (updated_at age) ───────────────────────
if [[ -n "$DASHBOARD_UPDATED_AT" ]]; then
    DASHBOARD_AGE_DAYS=$(python3 -c "
from datetime import datetime, timezone
import sys
try:
    updated = datetime.fromisoformat('$DASHBOARD_UPDATED_AT'.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    age_days = (now - updated).total_seconds() / 86400
    print(f'{age_days:.1f}')
except Exception as e:
    print('0')
" 2>/dev/null || echo "0")
    DASHBOARD_AGE_HOURS=$(python3 -c "
from datetime import datetime, timezone
try:
    updated = datetime.fromisoformat('$DASHBOARD_UPDATED_AT'.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    age_h = (now - updated).total_seconds() / 3600
    print(f'{age_h:.1f}')
except:
    print('?')
" 2>/dev/null || echo "?")
    if python3 -c "exit(0 if float('${DASHBOARD_AGE_DAYS}') > ${STALE_DAYS} else 1)" 2>/dev/null; then
        echo "⚠️  Dashboard updated_at is STALE: ${DASHBOARD_UPDATED_AT} (${DASHBOARD_AGE_DAYS} days ago)"
        echo "   ⚠️  This may indicate a caching issue on ninja66.ai — king SHA may still be valid"
        echo "   ⚠️  Continuing with SHA-based sync (staleness warning only, not a hard failure)"
    else
        echo "   Dashboard: ${DASHBOARD_UPDATED_AT} (${DASHBOARD_AGE_HOURS}h ago) ✓"
    fi
else
    echo "   Dashboard: updated_at field missing (proceeding with SHA sync)"
fi

# ── Step 3: Compare with local SHA ────────────────────────────────────────────
LOCAL_SHA=""
if [[ -f "$SHA_FILE" ]]; then
    LOCAL_SHA=$(cat "$SHA_FILE" | tr -d '[:space:]')  # strip whitespace/newlines
fi

echo "   Live SHA : ${LIVE_SHA:0:12}..."
echo "   Local SHA: ${LOCAL_SHA:0:12}..."
echo "   Repo     : $RUNTIME_REPO"

# ── Step 3b: Compare against GitHub HEAD (freshness check) ────────────────────
GITHUB_HEAD_SHA=$(curl -sf --max-time 10 "${GITHUB_API}/${RUNTIME_REPO}/commits/main" 2>/dev/null | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")

if [[ -n "$GITHUB_HEAD_SHA" ]] && [[ "$GITHUB_HEAD_SHA" != "$LIVE_SHA" ]]; then
    echo "   ⚠️  Dashboard SHA differs from GitHub HEAD: ${LIVE_SHA:0:12} vs ${GITHUB_HEAD_SHA:0:12}"
    echo "   ⚠️  This usually means the king is a private submission (runtime_repo=unarbos/ninja)"
    echo "      Dashboard SHA points to the promoted king commit, not latest repo changes."
elif [[ -n "$GITHUB_HEAD_SHA" ]]; then
    echo "   GitHub HEAD: ${GITHUB_HEAD_SHA:0:12} ✓ (matches dashboard)"
fi

OLD_LINES=0
if [[ -f "$KING_FILE" ]]; then
    OLD_LINES=$(wc -l < "$KING_FILE")
fi

# Already current?
if [[ "$LIVE_SHA" == "$LOCAL_SHA" ]] && [[ -f "$KING_FILE" ]] && [[ "$OLD_LINES" -ge "$MIN_LINES" ]]; then
    echo "✅ King is already current (${OLD_LINES}L) — no update needed"
    echo ""
    DASHBOARD_AGE_DISPLAY="${DASHBOARD_AGE_HOURS:-?}h ago"
    echo "KING_SYNC: ${LOCAL_SHA:0:8} → ${LIVE_SHA:0:8} | ${OLD_LINES}L | already-current | dashboard=${DASHBOARD_AGE_DISPLAY}"
    exit 0
fi

# ── Step 4: Fetch king from GitHub ────────────────────────────────────────────
FETCH_URL="https://raw.githubusercontent.com/${RUNTIME_REPO}/${LIVE_SHA}/agent.py"
echo "⬇️  Fetching king from: $FETCH_URL"

if ! curl -sf --max-time 60 "$FETCH_URL" -o "$TMP_KING"; then
    echo "❌ Failed to fetch king from GitHub"
    echo "   URL: $FETCH_URL"
    echo "   (Check if repo is public and SHA is valid)"
    exit 1
fi

# ── Step 4b: Package-shaped king → fetch modules and flatten ──────────────────
# The harness execs the king into a bare module named "agent" with no __path__,
# so `from agent.agent_loop import ...` can never resolve. A king whose agent.py
# is a thin entrypoint must be inlined before it can run at all.
if grep -qE '^from agent\.' "$TMP_KING"; then
    echo "📦 King is package-shaped — fetching agent/ modules and flattening"
    PKG_ROOT=$(mktemp -d)
    mkdir -p "$PKG_ROOT/agent"
    cp "$TMP_KING" "$PKG_ROOT/agent.py"

    PKG_BASE="https://raw.githubusercontent.com/${RUNTIME_REPO}/${LIVE_SHA}/agent"
    MODULES=$(curl -sf --max-time 30 \
        "${GITHUB_API}/${RUNTIME_REPO}/contents/agent?ref=${LIVE_SHA}" \
        | python3 -c "import json,sys; print(' '.join(e['name'] for e in json.load(sys.stdin) if e['name'].endswith('.py')))") || {
        echo "❌ Could not list the king's agent/ package"
        exit 1
    }
    for MOD in $MODULES; do
        if ! curl -sf --max-time 30 "${PKG_BASE}/${MOD}" -o "$PKG_ROOT/agent/${MOD}"; then
            echo "❌ Failed to fetch agent/${MOD}"
            exit 1
        fi
    done
    echo "   fetched: $(echo "$MODULES" | wc -w | tr -d ' ') modules"

    if ! python3 "$SCRIPT_DIR/flatten_king.py" "$PKG_ROOT" -o "$TMP_KING"; then
        echo "❌ Flattening the king failed"
        exit 1
    fi
    rm -rf "$PKG_ROOT"
fi

# ── Step 5: Validate downloaded file ──────────────────────────────────────────
NEW_LINES=$(wc -l < "$TMP_KING")

# Check minimum line count
if [[ "$NEW_LINES" -lt "$MIN_LINES" ]]; then
    echo "❌ Downloaded file is too short (${NEW_LINES}L < ${MIN_LINES}L minimum)"
    echo "   Possible truncated/empty download. Aborting."
    exit 1
fi

# solve() is the only thing the harness actually calls, so it is mandatory.
# SYSTEM_PROMPT / def main were markers of the old single-file king and are absent
# from the package king; requiring them made this script unable to ever sync a
# current king, which is how the local copy drifted far enough to hold a king with
# no reroll while the post-mortem was describing one.
if ! grep -qE "^def solve" "$TMP_KING"; then
    echo "❌ Downloaded king has no top-level solve()"
    exit 1
fi

MARKER_COUNT=0
for MARKER in "run_agent_loop" "collect_repo_patch" "wall_clock" "max_tokens"; do
    grep -q "$MARKER" "$TMP_KING" && MARKER_COUNT=$((MARKER_COUNT+1)) || true
done
if [[ "$MARKER_COUNT" -lt 2 ]]; then
    echo "❌ Downloaded file failed validation (only ${MARKER_COUNT}/4 agent markers found)"
    echo "   Expected at least 2 of: run_agent_loop, collect_repo_patch, wall_clock, max_tokens"
    exit 1
fi

# The king is exec'd, never imported as a package. Prove it loads the same way the
# harness loads it, before it is installed as the thing every gate run compares to.
if ! python3 -c "
import sys, types
p = '$TMP_KING'
m = types.ModuleType('agent'); m.__file__ = p; m.__spec__ = None
sys.modules['agent'] = m
exec(compile(open(p).read(), p, 'exec'), m.__dict__)
assert callable(m.solve), 'solve() is not callable'
"; then
    echo "❌ Downloaded king does not load under the harness's exec model"
    exit 1
fi

echo "   Validated: ${NEW_LINES}L, solve() loads harness-style, ${MARKER_COUNT}/4 markers ✓"

# ── Step 6: Backup + install ───────────────────────────────────────────────────
if [[ -f "$KING_FILE" ]]; then
    TS=$(date +%Y%m%d_%H%M%S)
    BACKUP="${KING_FILE}.bak.${TS}"
    cp "$KING_FILE" "$BACKUP"
    echo "   Backup  : $(basename "$BACKUP")"
fi

cp "$TMP_KING" "$KING_FILE"
echo "$LIVE_SHA" > "$SHA_FILE"

# ── Step 7: Summary ───────────────────────────────────────────────────────────
echo ""
echo "👑 King updated!"
echo "   ${LOCAL_SHA:0:12} → ${LIVE_SHA:0:12}"
echo "   Lines: ${OLD_LINES}L → ${NEW_LINES}L"
echo ""
echo "ℹ️  Pass to harness: --king king_agent.py --king-sha ${LIVE_SHA:0:12}"
echo ""
DASHBOARD_AGE_DISPLAY="${DASHBOARD_AGE_HOURS:-?}h ago"
echo "KING_SYNC: ${LOCAL_SHA:0:8} → ${LIVE_SHA:0:8} | ${NEW_LINES}L | updated | dashboard=${DASHBOARD_AGE_DISPLAY}"

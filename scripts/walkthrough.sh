#!/usr/bin/env bash
# 15-minute walkthrough: drives every scenario end to end and
# prints the access-log + audit-log rows that prove each one
# fired correctly.
#
# Run from the repo root:
#   ./scripts/walkthrough.sh
#
# Prerequisites:
#   * `docker compose up -d` is healthy.
#   * `uv sync` has installed the scenario clients' Python deps
#     into ./.venv (uv from https://docs.astral.sh/uv).
#
# Every client invocation below goes through `uv run` so the
# right interpreter and deps are picked up automatically.

set -euo pipefail

PROXY_URL="${PROXY_URL:-http://127.0.0.1:8080}"
ACCESS_LOG="${ACCESS_LOG:-/var/log/sbproxy/access.jsonl}"
AUDIT_LOG="${AUDIT_LOG:-/var/log/sbproxy/audit.jsonl}"

cd "$(dirname "$0")/.."

# --- helpers -----------------------------------------------------------

bar() {
  printf "\n========== %s ==========\n" "$*"
}

tail_access() {
  # Pull the last N lines of the access log; jq-pretty if jq is
  # available, raw otherwise.
  docker compose exec -T sbproxy tail -n "${1:-1}" "$ACCESS_LOG" \
    | (command -v jq >/dev/null && jq . || cat)
}

tail_audit() {
  docker compose exec -T sbproxy tail -n "${1:-1}" "$AUDIT_LOG" \
    | (command -v jq >/dev/null && jq . || cat)
}

wait_for_proxy() {
  for _ in $(seq 1 30); do
    if curl -fsS "${PROXY_URL%:*}:9090/readyz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "proxy did not become ready" >&2
  exit 1
}

# --- the six scenarios ------------------------------------------------

wait_for_proxy

bar "1. Agent detection"
echo
echo ">>> claude-code-like client (expect identified as claude-code-cli)"
uv run clients/claude_code_like.py "$PROXY_URL/anything" | head -3
echo
echo ">>> last access-log row:"
tail_access 1 | jq '{agent_id: .request.agent.id, score: .request.agent.score, provenance: .request.agent.provenance}'

echo
echo ">>> unsigned-scraper (expect no agent_id; trust_tier = Unknown or Suspicious)"
uv run clients/unsigned_scraper.py "$PROXY_URL/anything" | head -3
echo
echo ">>> last access-log row:"
tail_access 1 | jq '{agent_id: .request.agent.id, provenance: .request.agent.provenance, trust_tier: .request.trust_tier}'

bar "2. Web Bot Auth verification"
echo
echo ">>> signed-bot client (expect bot_auth.verified=true, trust_tier=VerifiedSigned)"
uv run clients/signed_bot.py "$PROXY_URL/anything" | head -3
echo
echo ">>> last access-log row:"
tail_access 1 | jq '{verified: .request.bot_auth.verified, trust_tier: .request.trust_tier}'

bar "3. AP2 mandate verification (ENTERPRISE)"
echo
echo ">>> ap2-payment client (expect 200, mandate verified, audit envelope)"
uv run clients/ap2_payment.py "$PROXY_URL/anything" | head -3
echo ">>> ap2-replay (expect first=200, second=409 Conflict)"
uv run clients/ap2_replay.py "$PROXY_URL/anything"
echo
echo ">>> last audit-log row (the MandateVerified event):"
tail_audit 1 | jq '{action: .action, target: .target, result: .result}' 2>/dev/null || echo "(enterprise audit not enabled; skip)"

bar "4. Agent budget enforcement"
echo
echo ">>> 50 req/s burst from the claude-code-like client (expect 429s)"
uv run clients/agent_budget_burst.py --duration-secs 5 "$PROXY_URL/anything"

bar "5. Prompt-linked audit (ENTERPRISE)"
echo
echo ">>> mcp-tool-call client (expect McpPromptLinkedAudit envelope)"
uv run clients/mcp_tool_call.py "$PROXY_URL/mcp/v1" | head -5 || true
echo
echo ">>> last audit-log row:"
tail_audit 1 | jq '{tool: .tool_name, prompt_digest, prompt_excerpt, agent_id, human_sponsor}' 2>/dev/null || echo "(enterprise audit not enabled; skip)"

bar "6. Trust tier (ENTERPRISE)"
echo
echo ">>> last 5 access-log rows show the trust_tier each request resolved to:"
tail_access 5 | jq -s 'map({status: .response.status, agent_id: .request.agent.id, verified: .request.bot_auth.verified, trust_tier: .request.trust_tier})'

bar "Walkthrough complete"
echo
echo "Inspect more:"
echo "  ./scripts/observe.sh        # follow the relevant log lines live"
echo "  ./scripts/reset.sh          # wipe state, rerun the walkthrough"
echo
echo "Per-scenario deep dives: docs/scenarios/0[1-6]-*.md"

# 15-minute walkthrough

Annotated read-through of every scenario `scripts/walkthrough.sh`
drives. Pair each section with the corresponding deep-dive doc
in `docs/scenarios/` for the wire-level detail.

## Pre-flight

```bash
docker compose up -d
docker compose ps                # all containers healthy?
curl -fsS http://127.0.0.1:9090/readyz | jq .
```

Expected: every service `running (healthy)`; `readyz` returns
HTTP 200 with `{"status":"ready"}`.

## Scenario 1 — Agent detection

```bash
uv run clients/claude_code_like.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/access.jsonl | jq .
```

Look for `request.agent.id = "claude-code-cli"` and
`request.agent.score = 95` on the access-log row. Then:

```bash
uv run clients/unsigned_scraper.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/access.jsonl | jq .
```

The scraper's row has `request.agent.provenance = "unsigned-anonymous"`
and `request.trust_tier = "Unknown"`. The proxy did NOT block;
it identified and stamped, letting the policy stack make the
deny call.

Detail: `docs/scenarios/01-agent-detection.md`.

## Scenario 2 — Web Bot Auth verification

```bash
uv run clients/signed_bot.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/access.jsonl | jq .
```

`request.bot_auth.verified = true` and `request.trust_tier =
"VerifiedSigned"`. Demonstrate the negative case by stripping
the `Signature` header (or just hand-running curl); the same
request returns 401 with `denial_reason = "bot_auth_signature_missing"`.

Detail: `docs/scenarios/02-web-bot-auth.md`.

## Scenario 3 — AP2 mandate verification (enterprise)

```bash
uv run clients/ap2_payment.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/audit.jsonl | jq .
uv run clients/ap2_replay.py http://127.0.0.1:8080/anything
```

`ap2-payment.py` returns 200 and the audit row's `action` is
`MandateVerified` with `result: success`. `ap2-replay.py` is
deliberately two-shot: the first hits 200, the second hits
`409 Conflict` because the mandate's `jti` already lives in the
proxy's nonce store.

Detail: `docs/scenarios/03-ap2-mandate.md`.

## Scenario 4 — Agent budget enforcement

```bash
uv run clients/agent_budget_burst.py --duration-secs 5 \
    http://127.0.0.1:8080/anything
```

The script prints a status-code histogram. With a 5/s cap and
50/s offered load you should see ~25 HTTP 200 and ~225 HTTP 429
across a 5-second window. The 429s carry `Retry-After`; check
one of them:

```bash
docker compose exec sbproxy tail -50 /var/log/sbproxy/access.jsonl \
    | jq -s '[.[] | select(.response.status == 429)] | length'
```

The 429 count matches the burst's overage.

Detail: `docs/scenarios/04-agent-budget.md`.

## Scenario 5 — Prompt-linked audit (enterprise)

```bash
uv run clients/mcp_tool_call.py http://127.0.0.1:8080/mcp/v1
docker compose exec sbproxy tail -1 /var/log/sbproxy/audit.jsonl | jq .
```

The envelope shape pairs the prompt with the tool call:

```json
{
  "schema_version": 0,
  "tool_name": "delete_file",
  "tool_arguments_digest": "sha256:...",
  "prompt_digest": "sha256:...",
  "prompt_excerpt": "Please clean up the obsolete schemas in staging-db",
  "agent_id": "claude-code-cli",
  "human_sponsor": "user:demo@example.com",
  "mcp_server": "demo-mcp",
  "upstream_status": 200,
  "duration_ms": 12
}
```

Detail: `docs/scenarios/05-prompt-linked-audit.md`.

## Scenario 6 — Trust tier

The trust-tier policy stamps every request the proxy serves. To
see the spread, run a mix:

```bash
uv run clients/claude_code_like.py http://127.0.0.1:8080/anything
uv run clients/signed_bot.py http://127.0.0.1:8080/anything
uv run clients/unsigned_scraper.py http://127.0.0.1:8080/anything

docker compose exec sbproxy tail -10 /var/log/sbproxy/access.jsonl \
    | jq -s 'group_by(.request.trust_tier) | map({tier: .[0].request.trust_tier, count: length})'
```

The histogram shows `VerifiedSigned`, `BehaviouralTrusted`, and
`Unknown` (or `Suspicious`) in roughly equal counts.

Detail: `docs/scenarios/06-trust-tier.md`.

## Cleanup

```bash
docker compose down -v
```

`-v` removes the postgres + sbproxy-logs volumes so the next
`up` starts from a clean slate.

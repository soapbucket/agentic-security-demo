# 15-minute walkthrough

Annotated read-through of every scenario `scripts/walkthrough.sh`
drives. Pair each section with the corresponding deep-dive doc
in `docs/scenarios/` for the wire-level detail.

## Pre-flight

```bash
docker compose up -d --build --wait
docker compose ps                # all containers healthy?
docker compose exec -T sbproxy wget -qO- http://127.0.0.1:9090/readyz
```

Expected: every service `running (healthy)`; `readyz` returns
HTTP 200 with `{"status":"ok"}`.

## Scenario 1 — Agent detection

```bash
uv run clients/claude_code_like.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/access.jsonl
```

Look for the Claude-Code wire shape on the access-log row:
`user_agent = "claude-cli/..."`, `x-stainless-arch`, and
`custom.demo_trust_tier = "BehaviouralTrusted"`.
Then:

```bash
uv run clients/unsigned_scraper.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/access.jsonl
```

The scraper's row has no Stainless tell and the demo stamps
`custom.demo_trust_tier = "Suspicious"` through a request header
so the walkthrough can show the trust-tier story without a private
enterprise build. The ADRF rule-pack scorer is enabled in the
gateway; v1.1.0 does not emit that scorer's named verdict as a
flat access-log field.

Detail: `docs/scenarios/01-agent-detection.md`.

## Scenario 2 — Web Bot Auth verification

```bash
uv run clients/signed_bot.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/access.jsonl
```

The signed request reaches the origin with `principal_kind =
"bot_auth"` in the access log. Demonstrate the negative case by
running the unsigned scraper against the same `botauth.demo.local`
host; the same route returns 401 before reaching the origin.

Detail: `docs/scenarios/02-web-bot-auth.md`.

## Scenario 3 — AP2 mandate verification

```bash
uv run clients/ap2_payment.py http://127.0.0.1:8080/anything
docker compose exec sbproxy tail -1 /var/log/sbproxy/audit.jsonl
uv run clients/ap2_replay.py http://127.0.0.1:8080/anything
```

`ap2-payment.py` returns 200 and the demo audit row's `action`
is `MandateVerified` with `result: success`. `ap2-replay.py` is
deliberately two-shot: the first hits 200, the second hits
`409 Conflict` because the mandate's `jti` already lives in the
mock origin's demo nonce store. In an enterprise deployment, that
same replay check belongs in the gateway policy.

Detail: `docs/scenarios/03-ap2-mandate.md`.

## Scenario 4 — Agent budget enforcement

```bash
uv run clients/agent_budget_burst.py --duration-secs 5 \
    http://127.0.0.1:8080/anything
```

The script prints a status-code histogram. The public demo uses
`on_anonymous: shared` with a deliberately small bucket
(`requests_per_minute: 10`, `burst: 5`) because v1.1.0 does not
accept inline demo agent-class catalogs. You should see some HTTP
200s and the rest HTTP 429. The 429s carry `Retry-After`; check
one of them:

```bash
docker compose exec sbproxy tail -50 /var/log/sbproxy/access.jsonl
```

The 429 count matches the burst's overage.

Detail: `docs/scenarios/04-agent-budget.md`.

## Scenario 5 — Prompt-linked audit

```bash
uv run clients/mcp_tool_call.py http://127.0.0.1:8080/mcp/v1
docker compose exec sbproxy tail -1 /var/log/sbproxy/audit.jsonl
```

The demo audit row pairs the prompt with the tool call:

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

The public demo stamps expected trust tiers into a custom access-log
field. To see the spread, run a mix:

```bash
uv run clients/claude_code_like.py http://127.0.0.1:8080/anything
uv run clients/signed_bot.py http://127.0.0.1:8080/anything
DEMO_HOST=audit.demo.local \
  uv run clients/unsigned_scraper.py http://127.0.0.1:8080/anything

docker compose exec sbproxy tail -10 /var/log/sbproxy/access.jsonl
```

The recent rows show `custom.demo_trust_tier` values such as
`VerifiedSigned`, `BehaviouralTrusted`, and `Suspicious`.

Detail: `docs/scenarios/06-trust-tier.md`.

## Cleanup

```bash
docker compose down -v
```

`-v` removes the postgres + sbproxy-logs volumes so the next
`up` starts from a clean slate.

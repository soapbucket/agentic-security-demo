# Scenario 6 — Trust tier

**Build tier**: Public demo mode. Enterprise deployments compute the
tier inside gateway policy.

## What it shows

Every request in the public demo is stamped with the expected trust
tier (`VerifiedSigned` / `BehaviouralTrusted` / `Suspicious`) in
`custom.demo_trust_tier`. This keeps the one-clone walkthrough
runnable without the private enterprise classifier while preserving
the downstream log and dashboard shape.

## How

The public config defines a custom access-log field:

```yaml
proxy:
  observability:
    log:
      custom_fields:
        - name: demo_trust_tier
          value: "${request.header.x-demo-trust-tier}"
```

The scenario clients set `X-Demo-Trust-Tier` to the verdict they
are meant to represent. In an enterprise deployment, that custom
field is replaced by the gateway-computed classifier result.

## Demo

Drive a mix of scenarios:

```bash
uv run clients/signed_bot.py          http://127.0.0.1:8080/anything
DEMO_HOST=audit.demo.local \
  uv run clients/claude_code_like.py  http://127.0.0.1:8080/anything
DEMO_HOST=audit.demo.local \
  uv run clients/unsigned_scraper.py  http://127.0.0.1:8080/anything
```

Then histogram the recent rows:

```bash
docker compose exec sbproxy tail -10 /var/log/sbproxy/access.jsonl
```

Expected:

```json
[
  {"custom":{"demo_trust_tier":"VerifiedSigned"}},
  {"custom":{"demo_trust_tier":"BehaviouralTrusted"}},
  {"custom":{"demo_trust_tier":"Suspicious"}}
]
```

## Policy hook

In a commercial gateway deployment, pair the computed tier with a
CEL deny rule to express "deny anything unknown in this origin":

```yaml
policies:
  - type: cel
    when: 'request.trust_tier == "Unknown"'
    action: deny
    deny_reason: "unknown_agent_blocked"
```

The trust-tier classifier is the verdict producer; the CEL policy
is the verdict consumer. Both are operator-tunable.

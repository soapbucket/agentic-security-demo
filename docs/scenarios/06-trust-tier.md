# Scenario 6 — Trust tier

**Build tier**: Enterprise.

## What it shows

Every request the proxy serves is stamped with a computed trust
tier (`VerifiedSigned` / `BehaviouralTrusted` / `Unknown` /
`Suspicious` / `Hostile`). One field downstream policies, log
queries, and dashboards key off, instead of re-deriving the
verdict from `agent.score` + `bot_auth.verified` + ... at every
consumer.

## How

The `trust_tier` policy is a closed-enum classifier evaluated
on every request after agent-detect + bot-auth + behaviour
signals have run. Tiers are first-match:

```yaml
- type: trust_tier
  levels:
    - name: VerifiedSigned
      when: 'request.bot_auth.verified == true'
    - name: BehaviouralTrusted
      when: 'request.agent.provenance == "unsigned-named"'
    - name: Unknown
      when: 'request.agent.provenance == "unsigned-anonymous"'
    - name: Suspicious
      when: 'request.agent.score >= 80 && request.bot_auth.verified == false'
    - name: Hostile
      when: 'request.policy.guardrail_hits > 0'
```

The verdict lands on `request.trust_tier`, gets stamped on the
access-log row, and is reachable from any downstream CEL or
Rego policy as `request.trust_tier`.

## Demo

Drive a mix of scenarios:

```bash
python clients/signed-bot.py          http://127.0.0.1:8080/anything
python clients/claude-code-like.py    http://127.0.0.1:8080/anything
python clients/unsigned-scraper.py    http://127.0.0.1:8080/anything
```

Then histogram the recent rows:

```bash
docker compose exec sbproxy tail -50 /var/log/sbproxy/access.jsonl \
    | jq -s 'group_by(.request.trust_tier)
             | map({tier: .[0].request.trust_tier, count: length})'
```

Expected:

```json
[
  {"tier": "VerifiedSigned",      "count": 1},
  {"tier": "BehaviouralTrusted",  "count": 1},
  {"tier": "Unknown",             "count": 1}
]
```

## Policy hook

Pair with a CEL deny rule to express "deny anything `Unknown`
in this origin":

```yaml
policies:
  - type: cel
    when: 'request.trust_tier == "Unknown"'
    action: deny
    deny_reason: "unknown_agent_blocked"
```

The trust-tier policy is the verdict-producer; the cel policy
is the verdict-consumer. Both are operator-tunable; the
trust-tier classifier ships sensible defaults that work
unchanged for most deployments.

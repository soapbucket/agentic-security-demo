# Scenario 4 — Agent budget enforcement

**Build tier**: OSS.

## What it shows

The `agent_budget` policy returning structured 429s when an
agent-shaped client exceeds its configured request budget. The
public artifact uses a shared anonymous bucket so it works with
the v1.1.0 release binary.

## How

In current sbproxy builds, `agent_budget` keys the bucket on the
resolved `agent_id`. The public v1.1.0 binary used here does not
accept inline demo agent-class catalogs, so this artifact sets
`on_anonymous: shared`; the fake Claude-Code burst still drains
one shared bucket and trips the same 429 path.

Demo config:

```yaml
policies:
  - type: agent_budget
    requests_per_minute: 10
    burst: 5
    on_exceed: deny
    on_anonymous: shared
```

## Demo

```bash
uv run clients/agent_budget_burst.py --duration-secs 5 \
    http://127.0.0.1:8080/anything
```

The client fires 50 in-flight requests from the Claude-Code wire
shape. Output:

```
fired: 50 in 5s (10.0/s)
  HTTP 200:   10 ( 20.0%)
  HTTP 429:   40 ( 80.0%)
```

Exact counts can vary with local timing. The important signal is
that the burst produces HTTP 429 responses after the small bucket
is exhausted.

Check one of the 429 rows for the `Retry-After`:

```bash
docker compose exec sbproxy tail -100 /var/log/sbproxy/access.jsonl
```

The response includes a `Retry-After: <seconds>` header that
tells the client when the bucket replenishes.

## Per-agent isolation

Per-agent isolation is the intended production shape when the
agent-class resolver catalog contains the agent identities. In the
public v1.1.0 demo, all unresolved callers share the anonymous
bucket. To test isolation with a newer build, add catalog entries
for the demo agents and switch the scenario back to named buckets:

```bash
agent_classes:
  catalog: inline
  entries:
    - id: claude-code-cli
      vendor: Anthropic
      purpose: assistant
      expected_user_agent_pattern: "^claude-cli/"
```

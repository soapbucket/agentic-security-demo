# Scenario 4 — Agent budget enforcement

**Build tier**: OSS.

## What it shows

A per-agent rate limit keyed on the resolved agent identity. A
Claude-Code-shape client firing 50/s into a 5/s cap sees the
proxy admit ~5/s and 429 the rest, with `Retry-After` headers
on the 429s.

## How

The proxy's `agent_budget` policy keys the rate-limit bucket on
`request.agent.id` (the value the `agent_detect` step stamped).
Bursts above the configured cap return 429 with `Retry-After`.

Demo config:

```yaml
policies:
  - type: agent_budget
    per_second: 5
    burst: 10
    headers:
      enabled: true
      include_retry_after: true
```

## Demo

```bash
uv run clients/agent_budget_burst.py --duration-secs 5 \
    http://127.0.0.1:8080/anything
```

The client fires 50 in-flight requests per second from a single
agent identity (`claude-code-cli`). Output:

```
fired: 250 in 5s (50.0/s)
  HTTP 200:   30 ( 12.0%)
  HTTP 429:  220 ( 88.0%)
```

The 200 count (~30) is the 5/s admit rate * 5 seconds + the
small burst (10). Everything else hit the budget.

Check one of the 429 rows for the `Retry-After`:

```bash
docker compose exec sbproxy tail -100 /var/log/sbproxy/access.jsonl \
    | jq -s '[.[] | select(.response.status == 429)][-1]'
```

The response includes a `Retry-After: <seconds>` header that
tells the client when the bucket replenishes.

## Per-agent isolation

The budget keys on `request.agent.id`, NOT on IP or hostname.
A second client with a different agent identity hits its own
bucket. Demonstrate:

```bash
# In one terminal, drive the burst:
uv run clients/agent_budget_burst.py --duration-secs 10 \
    http://127.0.0.1:8080/anything &

# In another, hit with a different agent (the unsigned scraper):
uv run clients/unsigned_scraper.py http://127.0.0.1:8080/anything
```

The scraper's request returns 200 even while the
`claude-code-cli` bucket is exhausted, because it lives in a
different budget bucket (`unsigned-anonymous`).

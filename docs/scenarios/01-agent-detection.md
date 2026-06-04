# Scenario 1 — Agent detection

**Build tier**: OSS (works against `ghcr.io/soapbucket/sbproxy:1.0`).

## What it shows

The proxy identifies named AI agents (Claude Code, Cursor,
OpenAI SDK shapes, etc.) from the wire shape of their requests
(User-Agent + headers + JA4 TLS fingerprint). The same matcher
flags unknown traffic as `unsigned-anonymous` so downstream
policy can deny-by-default.

## How

The proxy's `agent_detect` step consumes an ADRF
([Agent Detection Rule Format](https://github.com/soapbucket/adrf-spec))
rule pack. The demo's pack is at
`sbproxy-config/baseline.adrf.yaml` and includes two named-agent
rules: `claude-code-cli` and `openai-operator`. When a request
matches a rule the proxy stamps:

| Field on request context | Source |
|---|---|
| `agent.id` | rule's `id` |
| `agent.provenance` | rule's `provenance` (`unsigned-named` for matched, `unsigned-anonymous` for unmatched) |
| `agent.score` | rule's `score` (0..100) |

Every downstream policy and the access log key off these
fields.

## Demo

```bash
python clients/claude-code-like.py http://127.0.0.1:8080/anything
```

The client mimics Claude Code's wire shape: UA prefix
`claude-cli/`, the OpenAI-Stainless `x-stainless-*` header set
(the rule keys off `x-stainless-arch` as the corroborating
header tell).

The access-log row carries:

```json
{
  "request": {
    "agent": {
      "id": "claude-code-cli",
      "provenance": "unsigned-named",
      "score": 95
    }
  }
}
```

Now the negative case:

```bash
python clients/unsigned-scraper.py http://127.0.0.1:8080/anything
```

This client sends `Mozilla/5.0 (compatible; scraper/0)` with
no identifying headers. The proxy's matcher returns no rule;
the trust-tier policy resolves to `Unknown`. The access-log row
carries:

```json
{
  "request": {
    "agent": {
      "id": "",
      "provenance": "unsigned-anonymous",
      "score": 0
    },
    "trust_tier": "Unknown"
  }
}
```

## What it does NOT show

The OSS gateway does not deny on `Unknown`. The deny call is a
trust-tier policy decision that depends on operator intent;
the demo's policy stack admits everything and stamps the tier
so the access log carries the verdict. A real deployment pairs
the stamp with an `if request.trust_tier == "Unknown" then deny`
CEL policy or its equivalent.

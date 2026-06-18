# Scenario 1 — Agent detection

**Build tier**: OSS public-release image built by this repo.

## What it shows

The proxy runs an ADRF rule-pack scorer over AI-agent wire shapes
(User-Agent + headers + JA4 TLS fingerprint when available). The
public walkthrough shows the Claude-Code-shaped request and the
unsigned scraper side by side, then uses a demo trust-tier field
to make the expected classification visible in the access log.

## How

The proxy's `agent_detect` step consumes an ADRF
([Agent Detection Rule Format](https://github.com/soapbucket/adrf-spec))
rule pack. The demo's pack is at
`sbproxy-config/baseline.adrf.yaml` and includes two named-agent
rules: `claude-code-cli` and `openai-operator`. When a request
matches a rule, the scorer produces:

| Signal | Source |
|---|---|
| `request.agent.id` | rule's `id` in policy/CEL context |
| `request.agent.score` / `confidence` | ADRF rule score |
| `custom.demo_trust_tier` | demo-mode expected tier stamped by the client |

The v1.1.0 access-log schema does not flatten the ADRF verdict
into `agent_id` for this synthetic client, so the demo prints the
wire-shape headers plus `custom.demo_trust_tier`.

## Demo

```bash
uv run clients/claude_code_like.py http://127.0.0.1:8080/anything
```

The client mimics Claude Code's wire shape: UA prefix
`claude-cli/`, the OpenAI-Stainless `x-stainless-*` header set
(the rule keys off `x-stainless-arch` as the corroborating
header tell).

The access-log row carries:

```json
{
  "origin": "demo.local",
  "status": 200,
  "user_agent": "claude-cli/1.2.3 (external, cli)",
  "request_headers": {
    "x-stainless-arch": "arm64"
  },
  "custom": {
    "demo_trust_tier": "BehaviouralTrusted"
  }
}
```

Now the negative case:

```bash
uv run clients/unsigned_scraper.py http://127.0.0.1:8080/anything
```

This client sends `Mozilla/5.0 (compatible; scraper/0)` with no
identifying headers. The proxy's matcher returns no named rule.
The access-log row carries:

```json
{
  "origin": "demo.local",
  "status": 200,
  "custom": {
    "demo_trust_tier": "Suspicious"
  }
}
```

## What it does NOT show

The OSS gateway does not ship the enterprise trust-tier policy.
The public demo therefore stamps an expected tier into a custom
access-log field. In an enterprise deployment, that field is
replaced by the gateway-computed trust tier and can feed a CEL
deny policy or its equivalent.

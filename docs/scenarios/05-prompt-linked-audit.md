# Scenario 5 — Prompt-linked audit

**Build tier**: Public demo mode. Enterprise deployments emit this
from the gateway audit pipeline.

## What it shows

For every MCP `tools/call` sent through the demo route, the audit
log gets an `McpPromptLinkedAudit`-shaped envelope binding the
originating prompt (digest + 200-char excerpt) to the tool call
(name + arguments digest) plus the resolved agent and human
sponsor. Answers "what prompt caused this API call?" from one row.

## How

The public demo sends the MCP request through sbproxy to the mock
origin. The mock origin reads `params._meta.conversation`, computes
the prompt and argument digests, and appends the envelope to
`/var/log/sbproxy/audit.jsonl` in the shared log volume. In an
enterprise deployment, this event comes from the gateway audit
pipeline instead of the mock origin.

The fields the operator queries on:

| Field | Use |
|---|---|
| `prompt_digest` | join to access log; prove "same prompt" |
| `prompt_excerpt` | triage: recognise the prompt without reading the full body |
| `tool_arguments_digest` | prove "same arguments" without leaking the body |
| `agent_id` | which agent drove the call |
| `human_sponsor` | who is at the top of the credential chain |
| `mcp_server` | which upstream the call hit |
| `upstream_status` | what the upstream returned |

## Demo

```bash
uv run clients/mcp_tool_call.py http://127.0.0.1:8080/mcp/v1
```

The client sends a `tools/call` for `delete_file` with the
conversation context that led to the call inline in
`params._meta.conversation`.

Audit-log row (one line in `/var/log/sbproxy/audit.jsonl`):

```json
{
  "schema_version": 0,
  "tool_name": "delete_file",
  "tool_arguments_digest": "sha256:c4f...",
  "prompt_digest": "sha256:8b1...",
  "prompt_excerpt": "Please clean up the obsolete schemas in staging-db",
  "agent_id": "claude-code-cli",
  "human_sponsor": "user:demo@example.com",
  "mcp_server": "demo-mcp",
  "upstream_status": 200,
  "duration_ms": 12
}
```

## PocketOS reconstruction

The PocketOS incident: an AI agent under a real user's
credentials drove a tool call that wiped a production DB. From
the rows of the audit chain a triager answers:

1. **Which prompt drove the call?** `prompt_digest` +
   `prompt_excerpt` on the row.
2. **Who was the human?** `human_sponsor`.
3. **Which tool did what?** `tool_name` +
   `tool_arguments_digest`.

All three on one row. No log-joining required. The chain itself
is hash-linked so a malicious in-the-middle cannot rewrite a
prior row without breaking the chain (the operator's verifier
CLI catches the break).

## Privacy

The full prompt and the raw tool arguments are not persisted in the
demo envelope; only digests plus the 200-char excerpt are written.
Enterprise deployments can run that excerpt through the same PII
redactor the access log uses or set the excerpt length to zero.

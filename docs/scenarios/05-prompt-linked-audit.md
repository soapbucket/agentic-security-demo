# Scenario 5 — Prompt-linked audit

**Build tier**: Enterprise.

## What it shows

For every MCP `tools/call` the proxy observes, the audit chain
gets an `McpPromptLinkedAudit` envelope binding the originating
prompt (digest + 200-char redacted excerpt) to the tool call
(name + arguments digest) plus the resolved agent and human
sponsor. Answers "what prompt caused this API call?" from one
row, which is the audit gap the PocketOS 9-second prod-DB
delete and the Cursor CurXecute / MCPoison incidents share.

## How

The enterprise MCP audit pipeline subscribes to the OSS
`mcp_audit` structured-log target. On every tool call it pulls
the prior conversation context out of the request body (or the
proxy's session state), runs the prompt through the operator's
PII redactor, and emits the envelope on the hash-chained signed
audit log.

The envelope shape lives in
`sbproxy-enterprise-audit::mcp_prompt::McpPromptLinkedAudit`.
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
python clients/mcp-tool-call.py http://127.0.0.1:8080/mcp/v1
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

The full prompt and the raw tool arguments are NEVER on the
envelope; only digests + the 200-char excerpt that runs through
the same PII redactor the access log uses. Operators that want
zero raw-prompt content on the audit chain can also drop the
excerpt (set `excerpt_max_chars: 0`).

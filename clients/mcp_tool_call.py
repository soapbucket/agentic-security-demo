"""Scenario 5: prompt-linked audit envelope on an MCP tool call.

Drives an MCP `tools/call` against the proxy's MCP federation
endpoint, carrying the conversation context that led to the call
in the `messages` array per the MCP spec. The proxy emits an
`McpPromptLinkedAudit` envelope on the audit chain that binds:

  * the originating prompt (sha256 + 200-char redacted excerpt)
  * the tool name + arguments digest
  * the resolved agent + human sponsor
  * the upstream status

so triage can answer "what prompt caused this API call?" from
one row.

Usage:
  python mcp-tool-call.py http://127.0.0.1:8080/mcp/v1
"""

import json
import os
import sys
import urllib.request
import uuid


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/mcp/v1"

    request_body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/call",
        "params": {
            "name": "delete_file",
            "arguments": {"path": "/tmp/demo.txt"},
            # Conversation context the proxy uses to build the
            # prompt digest + excerpt. In a real MCP session the
            # client carries this in `_meta.conversation` or via
            # session state; the demo includes it inline.
            "_meta": {
                "conversation": [
                    {
                        "role": "user",
                        "content": "Please clean up the obsolete schemas in staging-db",
                    },
                    {
                        "role": "assistant",
                        "content": "I'll delete /tmp/demo.txt to clear scratch space.",
                    },
                ]
            },
        },
    }

    req = urllib.request.Request(
        url,
        method="POST",
        data=json.dumps(request_body).encode("utf-8"),
    )
    req.add_header("Host", os.environ.get("DEMO_HOST", "audit.demo.local"))
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "claude-cli/1.2.3 (external, cli)")
    req.add_header("x-stainless-arch", "arm64")
    req.add_header("x-demo-trust-tier", "BehaviouralTrusted")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"HTTP {resp.status}")
            print(resp.read().decode("utf-8")[:500])
            print()
            print("Check the audit chain for the McpPromptLinkedAudit envelope:")
            print("  docker compose exec sbproxy tail -1 /var/log/sbproxy/audit.jsonl)")
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:500])
        return 1


if __name__ == "__main__":
    sys.exit(main())

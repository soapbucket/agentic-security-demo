"""Scenario 1: Claude-Code-shape client.

Mimics the wire shape Claude Code emits: User-Agent prefix
`claude-cli/`, the OpenAI-Stainless SDK header set
(`x-stainless-arch`, etc.). The proxy's agent_detect step
recognises the prefix + header tell and stamps
the ADRF verdict on the request context. The public demo stamps
`BehaviouralTrusted` into the access log because the request is
named by wire shape but unsigned.

Usage:
  python claude-code-like.py http://127.0.0.1:8080/anything

This single shot is what scenario 1 calls. Scenario 4's
agent_budget exercise runs the burst variant below.
"""

import os
import sys
import urllib.request


def request_with_claude_code_shape(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Host", os.environ.get("DEMO_HOST", "demo.local"))
    req.add_header(
        "User-Agent",
        "claude-cli/1.2.3 (external, cli)",
    )
    # Stainless SDK header set; the proxy keys off `x-stainless-arch`
    # as the corroborating signal.
    req.add_header("x-stainless-arch", "arm64")
    req.add_header("x-stainless-os", "Darwin")
    req.add_header("x-stainless-runtime", "node")
    req.add_header("x-demo-trust-tier", "BehaviouralTrusted")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # 429 or similar still useful
        return exc.code, exc.read().decode("utf-8", errors="replace")


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/anything"
    status, body = request_with_claude_code_shape(url)
    print(f"HTTP {status}")
    print(body[:500])
    return 0 if 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())

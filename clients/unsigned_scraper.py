"""Scenario 1 (negative): unsigned-scraper.

Carries no agent-identifying UA and no signature. The proxy's
agent_detect step does NOT match any named-agent rule, so the
trust-tier policy stamps `Unknown` (or `Suspicious` if behaviour
signals fire). Demonstrates the deny-by-default posture for
unknown traffic when the operator configures it.

Usage:
  python unsigned-scraper.py http://127.0.0.1:8080/anything
"""

import os
import sys
import urllib.request


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/anything"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Host", os.environ.get("DEMO_HOST", "demo.local"))
    # Generic UA, no identifying headers, no signature. The
    # proxy's policy stack sees an unmatched anonymous request.
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; scraper/0)")
    req.add_header("x-demo-trust-tier", "Suspicious")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"HTTP {resp.status}")
            print(resp.read().decode("utf-8")[:500])
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}")
        print(exc.read().decode("utf-8", errors="replace")[:500])
        return 1


if __name__ == "__main__":
    sys.exit(main())

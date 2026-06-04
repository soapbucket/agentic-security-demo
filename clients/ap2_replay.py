"""Scenario 3 (negative): replay the same AP2 Cart Mandate.

Sends the same Cart Mandate twice in succession. The proxy's
mandate nonce store catches the second submission and returns
`409 Conflict` with a structured error body. Demonstrates the
replay-protection guarantee the `accept_payment` policy ships
with.

Usage:
  python ap2-replay.py http://127.0.0.1:8080/anything
"""

import sys
import time

# Reuse the minting helper from the happy-path client so both
# scenarios share the SD-JWT shape. `uv run` sets cwd to the
# repo root, so make sure the sibling client is importable
# regardless of where the script is invoked from.
import os.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# pylint: disable=import-error,wrong-import-position
from ap2_payment import mint_cart_mandate  # type: ignore  # sibling script

import urllib.request


def submit(url: str, sd_jwt: str) -> tuple[int, str]:
    req = urllib.request.Request(url, method="POST", data=b'{"intent":"purchase"}')
    req.add_header("Host", "demo.local")
    req.add_header("User-Agent", "ap2-replay-demo/0.1")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-Payment-Mandate", sd_jwt)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")[:500]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")[:500]


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/anything"

    mandate_id = f"demo-replay-{int(time.time())}"
    sd_jwt = mint_cart_mandate(mandate_id)

    print("--- first submission (expected: 200 OK) ---")
    s1, b1 = submit(url, sd_jwt)
    print(f"HTTP {s1}")
    print(b1)

    print("--- replay (expected: 409 Conflict, mandate already redeemed) ---")
    s2, b2 = submit(url, sd_jwt)
    print(f"HTTP {s2}")
    print(b2)

    # Demo passes when first succeeds and second is rejected.
    return 0 if s1 == 200 and s2 == 409 else 1


if __name__ == "__main__":
    sys.exit(main())

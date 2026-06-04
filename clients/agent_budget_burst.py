"""Scenario 4: agent budget enforcement.

Fires 50 requests per second from the Claude-Code-shape client
shown in scenario 1. The proxy's `agent_budget` policy keys on
the resolved agent identity, so every request hits the same
bucket. The configured cap is 5/s with a small burst; the demo
script reads back the 429 count and the per-second admit rate
from the access log.

Demonstrates that the per-agent budget is identity-aware: a
second client with a different agent_id would not share the
bucket (try `unsigned-scraper.py` in parallel to confirm).

Usage:
  python agent-budget-burst.py [--duration-secs 5] http://127.0.0.1:8080/anything
"""

import argparse
import concurrent.futures
import sys
import time
import urllib.request


def fire_one(url: str) -> int:
    req = urllib.request.Request(url, method="GET")
    req.add_header("Host", "demo.local")
    req.add_header("User-Agent", "claude-cli/1.2.3 (external, cli)")
    req.add_header("x-stainless-arch", "arm64")
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-secs", type=int, default=5)
    ap.add_argument(
        "url",
        nargs="?",
        default="http://127.0.0.1:8080/anything",
    )
    args = ap.parse_args()

    end = time.time() + args.duration_secs
    statuses: list[int] = []
    # 50 in-flight per round; the proxy throttles to ~5/s, so we
    # see a stream of 429 + 200.
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as pool:
        while time.time() < end:
            batch = [pool.submit(fire_one, args.url) for _ in range(50)]
            for f in batch:
                statuses.append(f.result())
            time.sleep(1)

    total = len(statuses)
    by_code: dict[int, int] = {}
    for s in statuses:
        by_code[s] = by_code.get(s, 0) + 1
    print(f"fired: {total} in {args.duration_secs}s ({total / args.duration_secs:.1f}/s)")
    for code, count in sorted(by_code.items()):
        pct = 100 * count / total
        print(f"  HTTP {code:>3}: {count:>4} ({pct:5.1f}%)")
    # Demo passes when the proxy actually throttles (a meaningful
    # share of the burst returns 429).
    return 0 if by_code.get(429, 0) > 0 else 1


if __name__ == "__main__":
    sys.exit(main())

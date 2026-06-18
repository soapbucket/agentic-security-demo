"""Scenario 3 (happy path): valid AP2 Cart Mandate against x402.

Constructs an SD-JWT Cart Mandate signed with the demo's AP2
fixture key (paired with /.well-known/ap2-jwks.json on the
origin), attaches it to the x402 Payment-Required handshake, and
sends it to the proxy. The proxy's `accept_payment` policy with
`rail: x402` + `mandate.require: cart` verifies the mandate and
admits the request.

Pair with `ap2-replay.py` to show the second submission of the
same mandate gets `409 Conflict` from the mandate nonce store.

The Cart Mandate's payload is a minimal AP2 v0.2 shape; the
client uses python-jose to sign the SD-JWT. Demo only; real
deployments mint mandates via the wallet provider, not in-band.

Usage:
  python ap2-payment.py [--mandate-id ID] http://127.0.0.1:8080/anything
"""

import argparse
import os
import sys
import time
import urllib.request

try:
    from jose import jwt
except ImportError:  # pragma: no cover
    print("install: pip install python-jose[cryptography]", file=sys.stderr)
    sys.exit(2)


# Demo AP2 signing key. Public half is at
# mock-origin/server.py's /.well-known/ap2-jwks.json. Deterministic
# fixture; never use in production.
_AP2_PRIVATE_KEY = {
    "kty": "EC",
    "crv": "P-256",
    "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
    "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
    "d": "870MB6gfuTJ4HtUnUvYMyJpr5eUZNP4Bk43bVdj3eAE",
}
_KID = "demo-ap2-1"


def mint_cart_mandate(mandate_id: str) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://issuer.demo.local/",
        "vct": "mandate.checkout.1",
        "jti": mandate_id,
        "iat": now,
        "exp": now + 300,
        "merchant": {
            "id": "demo.merchant",
            "name": "Demo Merchant Ltd",
        },
        "cart": {
            "total": {"amount": "4999", "currency": "USD"},
            "items": [
                {"sku": "demo-widget", "qty": 1, "price": "4999"},
            ],
        },
    }
    headers = {"kid": _KID, "alg": "ES256", "typ": "JWT"}
    return jwt.encode(claims, _AP2_PRIVATE_KEY, algorithm="ES256", headers=headers)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mandate-id", default=f"demo-cart-{int(time.time())}")
    ap.add_argument(
        "url",
        nargs="?",
        default="http://127.0.0.1:8080/anything",
    )
    args = ap.parse_args()

    sd_jwt = mint_cart_mandate(args.mandate_id)

    req = urllib.request.Request(args.url, method="POST", data=b'{"intent":"purchase"}')
    req.add_header("Host", os.environ.get("DEMO_HOST", "ap2.demo.local"))
    req.add_header("User-Agent", "ap2-demo-client/0.1")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-demo-trust-tier", "VerifiedSigned")
    # The x402 payment header carries the SD-JWT mandate.
    req.add_header("X-Payment-Mandate", sd_jwt)
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

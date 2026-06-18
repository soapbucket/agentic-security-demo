"""Scenario 2: Web Bot Auth signed request.

Signs the request per RFC 9421 with a key whose public half is
served at /.well-known/web-bot-auth-keys on the mock origin. The
proxy's `bot_auth` provider fetches the key directory, verifies
the signature, and stamps `bot_auth.verified = true` on the
request. The trust-tier policy escalates to `VerifiedSigned`.

Pair with `unsigned-scraper.py` to show the same request without
the signature is denied.

The signing key is the Ed25519 fixture pair pinned in the demo.
This client uses PyNaCl for Ed25519; it is the only client with
an external dep.

Usage:
  python signed-bot.py http://127.0.0.1:8080/anything
"""

import base64
import os
import sys
import time
import urllib.parse
import urllib.request

try:
    import nacl.signing
except ImportError:  # pragma: no cover
    print("install: pip install pynacl", file=sys.stderr)
    sys.exit(2)


# Demo signing key. The public half is in
# mock-origin/server.py's /.well-known/web-bot-auth-keys.
# Deterministic fixture; never use in production.
_SIGNING_KEY_SEED_B64 = "nWGxne_9WmC6hEr0kuwsxERJxWl7MmkZcDusAxyuf2A"
_KID = "demo-signer-1"


def sign_b64(data: bytes) -> str:
    seed = base64.urlsafe_b64decode(_SIGNING_KEY_SEED_B64 + "=")
    signer = nacl.signing.SigningKey(seed)
    return base64.standard_b64encode(signer.sign(data).signature).decode("ascii")


def build_signed_request(url: str) -> urllib.request.Request:
    host = os.environ.get("DEMO_HOST", "botauth.demo.local")
    path = urllib.parse.urlsplit(url).path or "/"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Host", host)
    req.add_header("User-Agent", "openai-operator/0.1 (web-bot-auth)")
    req.add_header("x-demo-trust-tier", "VerifiedSigned")
    created = int(time.time())
    # RFC 9421 covers signature base + signature input headers.
    # The demo uses a minimal coverage set: @method @path @authority
    # + Date. Production deployments cover more.
    sig_input = (
        f'sig1=("@method" "@path" "@authority" "date");'
        f"created={created};keyid=\"{_KID}\";alg=\"ed25519\""
    )
    date_value = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(created))
    req.add_header("Date", date_value)
    req.add_header("Signature-Input", sig_input)
    # Build the signature base per RFC 9421 §2.5. Minimal subset
    # matching the sig_input above.
    base = (
        f'"@method": GET\n'
        f'"@path": {path}\n'
        f'"@authority": {host}\n'
        f'"date": {date_value}\n'
        f'"@signature-params": ("@method" "@path" "@authority" "date");'
        f"created={created};keyid=\"{_KID}\";alg=\"ed25519\""
    )
    sig_b64 = sign_b64(base.encode("utf-8"))
    req.add_header("Signature", f'sig1=:{sig_b64}:')
    return req


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080/anything"
    req = build_signed_request(url)
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

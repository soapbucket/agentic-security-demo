"""Mock origin: echoes the inbound request as JSON, plus the two
.well-known endpoints the demo's scenarios need.

Routes:
  GET  /                          alive check (200 "ok")
  GET  /anything                  echoes method/headers/query as JSON
  POST /anything                  echoes method/headers/body as JSON
  GET  /.well-known/web-bot-auth-keys
                                  static JSON key directory for the
                                  Web Bot Auth verifier (scenario 2)
  GET  /.well-known/ap2-jwks.json static JWKS for the AP2 mandate
                                  verifier (scenario 3)
"""

import json
import time

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/")
def alive() -> tuple[str, int]:
    return "ok", 200


@app.route("/anything", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def echo():
    # Mirror httpbin's /anything shape so existing demos work.
    payload = {
        "method": request.method,
        "headers": dict(request.headers),
        "args": request.args.to_dict(flat=True),
        "data": request.get_data(as_text=True),
        "origin": request.remote_addr,
        "url": request.url,
        "received_at": int(time.time()),
    }
    return jsonify(payload), 200


@app.get("/.well-known/web-bot-auth-keys")
def web_bot_auth_keys():
    """Static key directory the demo's `signed-bot` client signs
    against. The proxy's `bot_auth` provider fetches this on
    request to verify the RFC 9421 message signature. Keys are
    deterministic fixtures so the demo is reproducible offline."""
    return jsonify(
        {
            "keys": [
                {
                    "kid": "demo-signer-1",
                    "kty": "OKP",
                    "crv": "Ed25519",
                    # Deterministic fixture public key (not a secret).
                    # Pair private key lives in clients/keys/.
                    "x": "11qYAYKxCrfVS_7TyWQHOg7hcvPapiMlrwIaaPcHURo",
                    "use": "sig",
                }
            ],
            "signer_url": "https://signer.demo.local/",
        }
    ), 200


@app.get("/.well-known/ap2-jwks.json")
def ap2_jwks():
    """Static JWKS the AP2 mandate verifier resolves against.
    The demo's `ap2-payment` client signs Cart Mandates with the
    private half of this key."""
    return jsonify(
        {
            "keys": [
                {
                    "kid": "demo-ap2-1",
                    "kty": "EC",
                    "crv": "P-256",
                    "x": "MKBCTNIcKUSDii11ySs3526iDZ8AiTo7Tu6KPAqv7D4",
                    "y": "4Etl6SRW2YiLUrN5vfvVHuhp7x8PxltmWWlbbM4IFyM",
                    "alg": "ES256",
                    "use": "sig",
                }
            ]
        }
    ), 200


if __name__ == "__main__":
    # Local dev only; production runs under gunicorn (see Dockerfile).
    app.run(host="0.0.0.0", port=3000)

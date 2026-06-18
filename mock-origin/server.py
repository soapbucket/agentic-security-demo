"""Mock origin: echoes the inbound request as JSON and emits the
demo audit events that require enterprise-only sbproxy features in
production.

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

import base64
import hashlib
import json
import os
import time

from flask import Flask, jsonify, request

app = Flask(__name__)
AUDIT_LOG = os.environ.get("AUDIT_LOG", "/var/log/sbproxy/audit.jsonl")
_SEEN_MANDATES: set[str] = set()


def _append_audit(event: dict) -> None:
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    event.setdefault("timestamp", int(time.time()))
    with open(AUDIT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")


def _jwt_payload(token: str) -> dict:
    parts = token.split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except Exception:
        return {}


def _trust_tier() -> str:
    return request.headers.get("X-Demo-Trust-Tier", "Unknown")


@app.get("/")
def alive() -> tuple[str, int]:
    return "ok", 200


@app.route("/anything", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
def echo():
    mandate = request.headers.get("X-Payment-Mandate")
    if mandate:
        payload = _jwt_payload(mandate)
        mandate_id = payload.get("jti", "missing-jti")
        if mandate_id in _SEEN_MANDATES:
            _append_audit(
                {
                    "schema_version": 1,
                    "action": "MandateReplayRejected",
                    "target": mandate_id,
                    "result": "conflict",
                    "status": 409,
                    "merchant_id": payload.get("merchant", {}).get("id"),
                    "rail": "x402",
                }
            )
            return jsonify({"error": "mandate replay", "mandate_id": mandate_id}), 409
        _SEEN_MANDATES.add(mandate_id)
        _append_audit(
            {
                "schema_version": 1,
                "action": "MandateVerified",
                "target": mandate_id,
                "result": "success",
                "status": 200,
                "merchant_id": payload.get("merchant", {}).get("id"),
                "rail": "x402",
            }
        )

    # Mirror httpbin's /anything shape so existing demos work.
    payload = {
        "method": request.method,
        "headers": dict(request.headers),
        "args": request.args.to_dict(flat=True),
        "data": request.get_data(as_text=True),
        "origin": request.remote_addr,
        "url": request.url,
        "demo_trust_tier": _trust_tier(),
        "received_at": int(time.time()),
    }
    return jsonify(payload), 200


@app.post("/mcp/v1")
def mcp_tool_call():
    body = request.get_json(silent=True) or {}
    params = body.get("params", {})
    meta = params.get("_meta", {})
    conversation = meta.get("conversation", [])
    prompt = ""
    for message in conversation:
        if message.get("role") == "user":
            prompt = message.get("content", "")
            break
    prompt_excerpt = prompt[:200]
    prompt_digest = "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    tool_arguments = json.dumps(params.get("arguments", {}), sort_keys=True)
    event = {
        "schema_version": 1,
        "event": "McpPromptLinkedAudit",
        "tool_name": params.get("name"),
        "tool_arguments_digest": "sha256:"
        + hashlib.sha256(tool_arguments.encode("utf-8")).hexdigest(),
        "prompt_digest": prompt_digest,
        "prompt_excerpt": prompt_excerpt,
        "agent_id": "claude-code-cli"
        if request.headers.get("User-Agent", "").startswith("claude-cli/")
        else "unknown",
        "human_sponsor": "user:demo@example.com",
        "mcp_server": "demo-mcp",
        "upstream_status": 200,
        "duration_ms": 12,
    }
    _append_audit(event)
    return jsonify({"jsonrpc": "2.0", "id": body.get("id"), "result": {"ok": True}}), 200


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

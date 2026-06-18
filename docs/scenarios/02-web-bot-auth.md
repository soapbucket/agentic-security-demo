# Scenario 2 — Web Bot Auth verification

**Build tier**: OSS.

## What it shows

A signed agent request from a configured Ed25519 key is accepted;
the same route without the signature is denied.

## How

The proxy's `bot_auth` auth provider verifies an RFC 9421
`Signature` + `Signature-Input` header pair against the inline
Ed25519 fixture key in `sbproxy-config/sb.yml`.

## Demo

```bash
uv run clients/signed_bot.py http://127.0.0.1:8080/anything
```

Access-log row:

```json
{
  "origin": "botauth.demo.local",
  "status": 200,
  "principal_kind": "bot_auth",
  "custom": {
    "demo_trust_tier": "VerifiedSigned"
  }
}
```

Negative case (no signature):

```bash
curl -s -H 'Host: botauth.demo.local' -H 'User-Agent: openai-operator/0.1' \
    -i http://127.0.0.1:8080/anything | head -10
```

Response: `HTTP 401`. Other scenarios use different virtual hosts,
so this strict auth route can deny unsigned requests without
blocking the rest of the walkthrough.

## Signature coverage

The demo signs the minimal RFC 9421 set:

```
"@method"      GET
"@path"        /anything
"@authority"   botauth.demo.local
"date"         Tue, 03 Jun 2026 22:00:00 GMT
```

Production deployments cover more (`@target-uri`, `@scheme`,
relevant body-related parameters for write methods). The proxy's
verifier reads whichever set the `Signature-Input` header
declares; the directory key + algorithm are validated against
the request's `keyid`.

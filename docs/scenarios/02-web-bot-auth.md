# Scenario 2 — Web Bot Auth verification

**Build tier**: OSS.

## What it shows

A signed agent request from a key published in the operator's
trusted key directory is accepted with `bot_auth.verified = true`;
the same request without the signature is denied.

## How

The proxy's `bot_auth` auth provider verifies an RFC 9421
`Signature` + `Signature-Input` header pair against the signer's
published key directory (per the
[`draft-meunier-web-bot-auth`](https://datatracker.ietf.org/doc/draft-meunier-web-bot-auth/)
spec). The directory's URL lives in the operator config; the
proxy caches keys per the standard JWKS cache policy.

The demo's directory is the mock-origin's `/.well-known/web-bot-auth-keys`
endpoint (an Ed25519 fixture key).

## Demo

```bash
python clients/signed-bot.py http://127.0.0.1:8080/anything
```

Access-log row:

```json
{
  "request": {
    "bot_auth": { "verified": true, "signer_kid": "demo-signer-1" },
    "trust_tier": "VerifiedSigned"
  },
  "response": { "status": 200 }
}
```

Negative case (no signature):

```bash
curl -s -H 'Host: demo.local' -H 'User-Agent: openai-operator/0.1' \
    -i http://127.0.0.1:8080/anything | head -10
```

Response: `HTTP 401`. The access-log row carries
`denial_reason = "bot_auth_signature_missing"` when the operator
configures `allow_unsigned: false` (the demo defaults to
`allow_unsigned: true` so other scenarios can run; flip the
config to see the deny path).

## Signature coverage

The demo signs the minimal RFC 9421 set:

```
"@method"      GET
"@path"        /anything
"@authority"   demo.local
"date"         Tue, 03 Jun 2026 22:00:00 GMT
```

Production deployments cover more (`@target-uri`, `@scheme`,
relevant body-related parameters for write methods). The proxy's
verifier reads whichever set the `Signature-Input` header
declares; the directory key + algorithm are validated against
the request's `keyid`.

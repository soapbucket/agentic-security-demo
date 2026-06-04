# Scenario 3 — AP2 mandate verification

**Build tier**: Enterprise (requires `SBPROXY_LICENSE_KEY`).

## What it shows

A payment request carrying a valid AP2 Cart Mandate is accepted
and audited; the same mandate replayed gets `409 Conflict`.
Demonstrates the spec-grade replay protection that prevents the
"same authorisation, two charges" failure mode.

## How

The proxy's `accept_payment` policy with `rail: x402` +
`mandate.require: cart` verifies an SD-JWT Cart Mandate per the
[AP2 v0.2 spec](https://github.com/google-agentic-commerce/ap2).
Verification steps:

1. Parse the SD-JWT in the `X-Payment-Mandate` header.
2. Resolve the issuer's JWKS (cached); confirm signature.
3. Validate the claim set: `vct` is `mandate.checkout.1`, `iat`
   + `exp` within bounds, `merchant.id` matches the operator's
   configured merchant id, `cart.total` matches the request's
   total.
4. Atomic insert `jti` into the mandate nonce store. On
   conflict, return `409 Conflict` (the replay guard).

On success the proxy emits a `MandateVerified` audit event on
the hash-chained audit log.

## Demo

```bash
python clients/ap2-payment.py http://127.0.0.1:8080/anything
```

Audit-log row:

```json
{
  "action": "MandateVerified",
  "target": { "target_kind": "mandate", "jti": "demo-cart-1716..." },
  "result": "success",
  "after": {
    "merchant": "demo.merchant",
    "vct": "mandate.checkout.1",
    "cart_total_usd": "49.99"
  }
}
```

Replay:

```bash
python clients/ap2-replay.py http://127.0.0.1:8080/anything
```

The client sends the same Cart Mandate twice. First submission
returns 200. Second returns:

```
HTTP/1.1 409 Conflict
Content-Type: application/json

{"error":"mandate_replay","jti":"demo-cart-1716..."}
```

The audit log records both: first as `MandateVerified` /
success, second as `MandateVerified` / failure with
`decision = ReplayDetected`.

## What it does NOT show

The demo's nonce store is in-memory (per-pod). A real multi-pod
deployment wires the nonce store to Postgres so replay
detection works across pods. The `accept_payment` policy
accepts a `nonce_store: postgres` knob the demo does not
exercise.

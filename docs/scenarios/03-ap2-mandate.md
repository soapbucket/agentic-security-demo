# Scenario 3 — AP2 mandate verification

**Build tier**: Public demo mode. Enterprise deployments move this
check into sbproxy policy.

## What it shows

A payment request carrying a valid AP2 Cart Mandate is accepted
and audited; the same mandate replayed gets `409 Conflict`.
Demonstrates the spec-grade replay protection that prevents the
"same authorisation, two charges" failure mode.

## How

The public demo sends the request through sbproxy to the mock
origin. The mock origin decodes the SD-JWT-like mandate fixture,
records the `jti`, and emits the same audit shape the gateway
policy would produce in an enterprise deployment. Verification
steps represented by the demo:

1. Parse the SD-JWT in the `X-Payment-Mandate` header.
2. Decode the deterministic fixture claim set.
3. Validate the claim set shape: `vct` is `mandate.checkout.1`, `iat`
   + `exp` within bounds, `merchant.id` matches the operator's
   configured merchant id, `cart.total` matches the request's
   total.
4. Atomic insert `jti` into the mandate nonce store. On
   conflict, return `409 Conflict` (the replay guard).

On success the mock origin emits a `MandateVerified` event to the
demo audit log mounted into the sbproxy container.

## Demo

```bash
uv run clients/ap2_payment.py http://127.0.0.1:8080/anything
```

Audit-log row:

```json
{
  "action": "MandateVerified",
  "target": "demo-cart-1716...",
  "result": "success",
  "after": {
  "merchant_id": "demo.merchant",
  "rail": "x402"
}
```

Replay:

```bash
uv run clients/ap2_replay.py http://127.0.0.1:8080/anything
```

The client sends the same Cart Mandate twice. First submission
returns 200. Second returns:

```
HTTP/1.1 409 Conflict
Content-Type: application/json

{"error":"mandate replay","mandate_id":"demo-cart-1716..."}
```

The audit log records both: first as `MandateVerified` /
success, second as `MandateReplayRejected` / conflict.

## What it does NOT show

The demo's nonce store is in-memory in the mock-origin process.
A real multi-pod deployment wires replay protection into the
gateway's shared state store so detection works across pods.

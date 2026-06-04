# SBproxy Agentic Security Demo

Clone, `docker compose up`, and in 15 minutes you have a running
proxy demonstrating end-to-end agentic security: agent
identification, signed-bot verification, payment-mandate
verification, per-agent rate-limit enforcement, prompt-linked
audit, and per-request trust tiers.

## Quick start

```bash
git clone https://github.com/soapbucket/agentic-security-demo
cd agentic-security-demo
docker compose up -d
./scripts/walkthrough.sh
```

The walkthrough script drives every scenario in order and prints
the relevant lines from the access log / audit log as each lands.
Expected runtime end to end: ~12 minutes on a typical laptop.

For a CISO-friendly read-through with annotated outputs, see
[`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md). The
asciinema recording at [`docs/walkthrough.cast`](docs/walkthrough.cast)
replays the same flow in ~5 minutes.

## What you see

The demo wires six distinct capabilities into one running stack
and exercises each one with a representative client:

| # | Scenario | What the demo shows |
|---|---|---|
| 1 | **Agent detection** | A fake Claude-Code-shape client is identified by UA + headers + JA4; an unsigned scraper is flagged `Suspicious` instead |
| 2 | **Web Bot Auth verification** | A signed request from a `Signature-Agent`-shaped signer passes; the same request without the signature is denied |
| 3 | **AP2 mandate verification** | An x402 payment request carrying a valid AP2 Cart Mandate succeeds; a replayed mandate is rejected with `409 Conflict` |
| 4 | **Agent budget enforcement** | The fake Claude-Code client fires 50 req/s; the proxy throttles to the configured cap with structured `429`s |
| 5 | **Prompt-linked audit** | An MCP tool call is captured with the originating prompt + the upstream call linked by a single envelope on the audit chain |
| 6 | **Trust tier** | Each request shows its computed tier (`VerifiedSigned`, `BehaviouralTrusted`, `Unknown`, `Suspicious`, or `Hostile`) on the access log |

## Architecture

```
                       ┌──────────────────────┐
                       │  sbproxy (gateway)   │
                       │  ─────────────────   │
                       │  agent detect        │
  scenario clients ─▶  │  web bot auth        │ ─▶  mock origin
                       │  AP2 mandate verify  │
                       │  agent budget        │
                       │  prompt-linked audit │
                       └──────────┬───────────┘
                                  │
                       ┌──────────┴───────────┐
                       │   postgres + redis   │  ◀── operator state
                       └──────────────────────┘
```

Every container is in `docker-compose.yml`. Operators inspect
each capability via:

* Access log: `docker compose exec sbproxy tail -F /var/log/sbproxy/access.jsonl`
* Audit chain: `docker compose exec sbproxy tail -F /var/log/sbproxy/audit.jsonl`
* Metrics: <http://127.0.0.1:9090/metrics>

## Build requirements

* Docker 25+ with Compose v2.
* ~4 GB free RAM (Postgres + Redis + sbproxy + clients).
* Internet on first run (image pulls); the demo is offline after.

## Repo layout

```
agentic-security-demo/
├── README.md                  ◀ you are here
├── LICENSE                    ◀ Apache-2.0
├── docker-compose.yml         ◀ the full stack
├── sbproxy-config/
│   └── sb.yml                 ◀ proxy config wiring all 6 scenarios
├── mock-origin/               ◀ httpbin-shaped target API
│   └── server.py
├── clients/                   ◀ one client per scenario
│   ├── claude-code-like.py
│   ├── unsigned-scraper.py
│   ├── signed-bot.py
│   ├── ap2-payment.py
│   ├── ap2-replay.py
│   └── mcp-tool-call.py
├── scripts/
│   ├── walkthrough.sh         ◀ runs every scenario in order
│   ├── observe.sh             ◀ tails the relevant log lines
│   └── reset.sh               ◀ wipes state for a fresh run
└── docs/
    ├── WALKTHROUGH.md         ◀ annotated read-through
    ├── walkthrough.cast       ◀ asciinema recording
    └── scenarios/             ◀ one md per scenario with the wire details
        ├── 01-agent-detection.md
        ├── 02-web-bot-auth.md
        ├── 03-ap2-mandate.md
        ├── 04-agent-budget.md
        ├── 05-prompt-linked-audit.md
        └── 06-trust-tier.md
```

## Build notes

Some scenarios (AP2 mandate verification, prompt-linked audit,
trust tier) ride on the **SBproxy Enterprise** binary, not the
OSS sbproxy. The demo's `docker-compose.yml` defaults to the
enterprise image (`ghcr.io/soapbucket/sbproxy-enterprise:1.0`)
and reads the license key from `SBPROXY_LICENSE_KEY`. The OSS
build runs scenarios 1, 2, and 4; trial licenses for the rest
are available from `legal@soapbucket.com`.

Each scenario's doc names which build it requires up front.

## License

[Apache-2.0](LICENSE). The proxy image runs under its own
license (BSL 1.1 for OSS, commercial for enterprise); this demo
repo and its scripts / docs are permissively licensed so any
prospect can fork it without fee.

## Production resources

* [SBproxy docs](https://docs.sbproxy.dev)
* [Enterprise licensing](mailto:legal@soapbucket.com)
* [Issues for this demo](https://github.com/soapbucket/agentic-security-demo/issues)

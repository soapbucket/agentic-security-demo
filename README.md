# SBproxy Agentic Security Demo

Clone, `docker compose up`, and in 15 minutes you have a running
proxy demonstrating end-to-end agentic security: agent
identification, signed-bot verification, payment-mandate
verification, agent-budget rate-limit enforcement, prompt-linked
audit, and per-request trust tiers.

## Quick start

```bash
git clone https://github.com/soapbucket/agentic-security-demo
cd agentic-security-demo
docker compose up -d --build --wait
uv sync                    # installs the scenario clients' Python deps
./scripts/walkthrough.sh
```

The walkthrough drives each scenario client via `uv run` so you
do not need to activate the venv by hand. Install `uv` per
<https://docs.astral.sh/uv/getting-started/installation/>.

The walkthrough script drives every scenario in order and prints
the relevant lines from the access log / audit log as each lands.
Expected runtime end to end: ~12 minutes on a typical laptop.

For a CISO-friendly read-through with annotated outputs, see
[`docs/WALKTHROUGH.md`](docs/WALKTHROUGH.md). The
asciinema recording at [`docs/walkthrough.cast`](docs/walkthrough.cast)
replays the same flow in ~5 minutes.

## What you see

The demo wires six capabilities into one running stack and
exercises each one with a representative client. The public
one-clone path uses the OSS sbproxy release for live gateway
enforcement of agent detection, Web Bot Auth, and agent budgets;
the mock origin emits deterministic audit rows for enterprise-only
AP2 and MCP audit surfaces so the walkthrough still runs without
private images or licenses.

| # | Scenario | What the demo shows |
|---|---|---|
| 1 | **Agent detection** | A fake Claude-Code-shape client is identified by UA + headers + JA4; an unsigned scraper is flagged `Suspicious` instead |
| 2 | **Web Bot Auth verification** | A signed request from a `Signature-Agent`-shaped signer passes; the same request without the signature is denied |
| 3 | **AP2 mandate verification** | An x402 payment request carrying a valid AP2 Cart Mandate succeeds; a replayed mandate is rejected with `409 Conflict` |
| 4 | **Agent budget enforcement** | The fake Claude-Code client bursts above the configured public-demo budget; the proxy returns structured `429`s |
| 5 | **Prompt-linked audit** | An MCP tool call is captured with the originating prompt + the upstream call linked by a single envelope on the demo audit log |
| 6 | **Trust tier** | Each request shows the expected tier (`VerifiedSigned`, `BehaviouralTrusted`, `Suspicious`) on the access log |

## Architecture

```
                       ┌──────────────────────┐
                       │  sbproxy (gateway)   │
                       │  ─────────────────   │
                       │  agent detect        │
  scenario clients ─▶  │  web bot auth        │ ─▶  mock origin
                       │  AP2 demo route      │
                       │  agent budget        │
                       │  prompt audit route  │
                       └──────────┬───────────┘
                                  │
                       ┌──────────┴───────────┐
                       │   postgres + redis   │  ◀── operator state
                       └──────────────────────┘
```

Every container is in `docker-compose.yml`. Operators inspect
each capability via:

* Access log: `docker compose exec sbproxy tail -F /var/log/sbproxy/access.jsonl`
* Demo audit log: `docker compose exec sbproxy tail -F /var/log/sbproxy/audit.jsonl`
* Metrics: `docker compose exec -T sbproxy wget -qO- http://127.0.0.1:9090/metrics`

## Build requirements

* Docker 25+ with Compose v2.
* ~4 GB free RAM (Postgres + Redis + sbproxy + clients).
* Internet on first run (image pulls); the demo is offline after.

## Repo layout

```
agentic-security-demo/
├── README.md                  ◀ you are here
├── LICENSE                    ◀ Apache-2.0
├── pyproject.toml             ◀ uv sync installs the client deps
├── docker-compose.yml         ◀ the full stack
├── sbproxy-config/
│   └── sb.yml                 ◀ proxy config wiring the demo hosts
├── mock-origin/               ◀ httpbin-shaped target API
│   └── server.py
├── clients/                   ◀ one client per scenario, run via `uv run`
│   ├── claude_code_like.py
│   ├── unsigned_scraper.py
│   ├── signed_bot.py
│   ├── ap2_payment.py
│   ├── ap2_replay.py
│   ├── agent_budget_burst.py
│   └── mcp_tool_call.py
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

`docker-compose.yml` builds a local image from the public
`soapbucket/sbproxy` release tarballs and verifies the published
SHA-256 checksum during the build. Set `SBPROXY_VERSION=v1.1.0`
or another release tag to pin the binary.

The public demo does not pull private GHCR images. Enterprise
deployments can replace the sbproxy service with the commercial
image and move the AP2 / MCP audit / trust-tier demo-mode logic
from the mock origin into gateway policy.

## License

[Apache-2.0](LICENSE). The proxy image runs under its own
license (BSL 1.1 for OSS, commercial for enterprise); this demo
repo and its scripts / docs are permissively licensed so any
prospect can fork it without fee.

## Production resources

* [SBproxy docs](https://docs.sbproxy.dev)
* [Enterprise licensing](mailto:legal@soapbucket.com)
* [Issues for this demo](https://github.com/soapbucket/agentic-security-demo/issues)

#!/usr/bin/env bash
# Wipe demo state so the walkthrough runs from scratch:
# clear the access + audit logs, restart the mock origin (drops the
# in-memory nonce store for AP2 replay), and restart the proxy
# (resets the agent_budget token buckets).
#
# Run: ./scripts/reset.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo ">>> truncating logs"
docker compose exec -T sbproxy sh -c \
  "truncate -s 0 /var/log/sbproxy/access.jsonl /var/log/sbproxy/audit.jsonl"

echo ">>> restarting mock-origin and sbproxy"
docker compose restart mock-origin sbproxy

echo ">>> waiting for ready"
for _ in $(seq 1 30); do
  if docker compose exec -T sbproxy wget -qO- http://127.0.0.1:9090/readyz >/dev/null 2>&1; then
    echo ">>> ready"
    exit 0
  fi
  sleep 1
done

echo "proxy did not become ready after restart" >&2
exit 1

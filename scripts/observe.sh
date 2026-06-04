#!/usr/bin/env bash
# Tails the access log + audit log side by side so a presenter
# can keep the relevant rows on screen while driving the
# walkthrough by hand. Stop with Ctrl-C.
#
# Run: ./scripts/observe.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== access log (left)  +  audit log (right) ==="
echo "Ctrl-C to stop."
echo

# tmux-free side-by-side: paste both tails through awk so each
# line is prefixed with its source.
docker compose exec -T sbproxy tail -F /var/log/sbproxy/access.jsonl \
  | awk '{print "[access] " $0}' &
ACCESS_PID=$!

docker compose exec -T sbproxy tail -F /var/log/sbproxy/audit.jsonl \
  | awk '{print "[audit]  " $0}' &
AUDIT_PID=$!

trap 'kill $ACCESS_PID $AUDIT_PID 2>/dev/null || true' EXIT INT TERM
wait

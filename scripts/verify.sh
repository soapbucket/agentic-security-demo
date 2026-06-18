#!/usr/bin/env bash
# Repo-level validation for the demo artifact. Keeps the public
# "one clone" promise honest without needing provider credentials
# or a paid SBproxy Enterprise license.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "== shell syntax =="
bash -n scripts/*.sh

echo "== python syntax =="
python3 -m py_compile clients/*.py mock-origin/server.py

echo "== compose config =="
docker compose config --quiet

echo "== documentation links and cast =="
python3 - <<'PY'
import json
import pathlib
import re
import sys

root = pathlib.Path.cwd()
missing: list[str] = []

for md in [root / "README.md", root / "docs" / "WALKTHROUGH.md", *sorted((root / "docs" / "scenarios").glob("*.md"))]:
    text = md.read_text(encoding="utf-8")
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        path = target.split("#", 1)[0]
        if path and not (md.parent / path).resolve().exists():
            missing.append(f"{md.relative_to(root)} -> {target}")

cast = root / "docs" / "walkthrough.cast"
if not cast.exists():
    missing.append("docs/walkthrough.cast")
else:
    with cast.open("r", encoding="utf-8") as fh:
        header = json.loads(fh.readline())
        if header.get("version") != 2:
            missing.append("docs/walkthrough.cast must be asciinema v2")
        for line_no, line in enumerate(fh, start=2):
            event = json.loads(line)
            if not (isinstance(event, list) and len(event) == 3 and event[1] in {"o", "i"}):
                missing.append(f"docs/walkthrough.cast:{line_no} invalid event")
                break

if missing:
    print("validation failed:", file=sys.stderr)
    for item in missing:
        print(f"  - {item}", file=sys.stderr)
    sys.exit(1)
PY

echo "ok"

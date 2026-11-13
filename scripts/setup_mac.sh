#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo 'Install Python 3.11+ from python.org'; exit 1; }
command -v node >/dev/null || { echo 'Install Node 22.12+ from nodejs.org'; exit 1; }
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
node -e 'let [m,n]=process.versions.node.split(".").map(Number);if(m<22||(m===22&&n<12))throw Error("Node 22.12+ required")'
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
.venv/bin/python scripts/train_model.py
npm run build --prefix frontend
.venv/bin/python scripts/validate_project.py --application-only
echo 'Setup complete. Run bash scripts/run_demo.sh'

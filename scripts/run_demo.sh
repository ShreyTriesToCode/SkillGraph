#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] && [ -d frontend/node_modules ] || { echo 'Run bash scripts/setup_mac.sh first'; exit 1; }
for port in 8000 5173; do
 if lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null; then echo "Port $port is already in use. Stop its existing process first."; exit 1; fi
done
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
backend_pid=$!
(cd frontend && exec ./node_modules/.bin/vite --host 127.0.0.1 --port 5173 --strictPort) &
frontend_pid=$!
cleanup(){ kill "$backend_pid" "$frontend_pid" 2>/dev/null || true; wait "$backend_pid" "$frontend_pid" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
ready=0
for i in {1..40}; do
 if curl -fsS http://127.0.0.1:8000/api/health >/dev/null 2>&1 && curl -fsS http://127.0.0.1:5173/ >/dev/null 2>&1; then ready=1; break; fi
 if ! kill -0 "$backend_pid" 2>/dev/null || ! kill -0 "$frontend_pid" 2>/dev/null; then echo 'Service exited unexpectedly'; exit 1; fi
 sleep 1
done
[ "$ready" = 1 ] || { echo 'Startup timed out'; exit 1; }
echo 'SkillGraph: http://127.0.0.1:5173'
echo 'API docs: http://127.0.0.1:8000/docs'
echo 'Press Ctrl+C to stop both services.'
wait "$backend_pid" "$frontend_pid"

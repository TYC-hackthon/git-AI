#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/Backend"
FRONTEND_DIR="$ROOT_DIR/Frontend"

BACKEND_PORT="${BACKEND_PORT:-5000}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"

PIDS=()

cleanup() {
  if [ "${#PIDS[@]}" -gt 0 ]; then
    echo
    echo "Stopping dev servers..."
    kill "${PIDS[@]}" 2>/dev/null || true
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

trap cleanup EXIT INT TERM

require_command uv
require_command npm

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Installing backend dependencies..."
  (cd "$BACKEND_DIR" && uv sync)
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$FRONTEND_DIR" && npm install)
fi

echo "Starting backend on http://127.0.0.1:$BACKEND_PORT/"
(
  cd "$BACKEND_DIR"
  PORT="$BACKEND_PORT" uv run python main.py
) &
PIDS+=("$!")

echo "Starting frontend on http://$FRONTEND_HOST:3000/"
(
  cd "$FRONTEND_DIR"
  npm run dev -- --host "$FRONTEND_HOST"
) &
PIDS+=("$!")

wait -n "${PIDS[@]}"

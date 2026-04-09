#!/usr/bin/env bash
# Wait for frontend and backend to be ready, then open Edge.
# Used by "npm run dev:all" via concurrently.

FRONTEND_URL="http://localhost:5173"
BACKEND_URL="http://localhost:8000/api/v1/health"
EDGE="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
MAX_WAIT=30

waited=0
until curl -s -o /dev/null "$FRONTEND_URL" && curl -s -o /dev/null "$BACKEND_URL"; do
  sleep 1
  waited=$((waited + 1))
  if [ "$waited" -ge "$MAX_WAIT" ]; then
    echo "[open-browser] Timed out after ${MAX_WAIT}s waiting for servers."
    exit 0  # don't fail the dev process
  fi
done

echo "[open-browser] Servers ready — opening $FRONTEND_URL in Edge"
"$EDGE" "$FRONTEND_URL" &>/dev/null &

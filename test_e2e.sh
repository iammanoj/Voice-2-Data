#!/bin/bash
# ─── Voice-to-Data E2E Test Runner ─────────────────────────────────────────
# Starts backend, ngrok tunnel, creates VAPI assistant, starts frontend.
# Usage: ./test_e2e.sh

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[E2E]${NC} $1"; }
ok()   { echo -e "${GREEN}  ✓${NC} $1"; }
fail() { echo -e "${RED}  ✗${NC} $1"; }
warn() { echo -e "${YELLOW}  !${NC} $1"; }

cleanup() {
    log "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null && ok "Backend stopped"
    [ -n "$NGROK_PID" ] && kill $NGROK_PID 2>/dev/null && ok "ngrok stopped"
    [ -n "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null && ok "Frontend stopped"
    exit 0
}
trap cleanup INT TERM

# ─── Step 1: Validate prerequisites ────────────────────────────────────────
log "Step 1: Checking prerequisites..."

[ -f "$DIR/engagement.db" ] && ok "engagement.db found" || { fail "engagement.db missing — run: python3 generate_data.py"; exit 1; }
[ -f "$DIR/.env" ] && ok ".env found" || { fail ".env missing — copy .env.example to .env and fill in VAPI_API_KEY"; exit 1; }
[ -f "$DIR/frontend/.env" ] && ok "frontend/.env found" || { fail "frontend/.env missing — copy frontend/.env.example to frontend/.env"; exit 1; }

python3 -c "import fastapi" 2>/dev/null && ok "FastAPI installed" || { fail "FastAPI missing — run: pip3 install fastapi uvicorn"; exit 1; }
which ngrok >/dev/null 2>&1 && ok "ngrok installed" || { fail "ngrok missing — run: brew install ngrok"; exit 1; }
which node >/dev/null 2>&1 && ok "Node.js installed" || { fail "Node.js missing"; exit 1; }

# ─── Step 2: Start backend ─────────────────────────────────────────────────
log "Step 2: Starting backend on port 8000..."
python3 "$DIR/server.py" &
BACKEND_PID=$!
sleep 2

if curl -s http://localhost:8000/health | grep -q '"ok"'; then
    ok "Backend healthy (PID $BACKEND_PID)"
else
    fail "Backend failed to start"
    exit 1
fi

# ─── Step 3: Start ngrok tunnel ────────────────────────────────────────────
log "Step 3: Starting ngrok tunnel..."
ngrok http 8000 --log=stdout --log-level=warn > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!
sleep 3

NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "
import sys, json
try:
    tunnels = json.load(sys.stdin)['tunnels']
    for t in tunnels:
        if t['proto'] == 'https':
            print(t['public_url'])
            break
except: pass
" 2>/dev/null)

if [ -n "$NGROK_URL" ]; then
    ok "ngrok tunnel: $NGROK_URL"
else
    fail "ngrok failed — is it authenticated? Run: ngrok config add-authtoken <token>"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

# ─── Step 4: Update .env with ngrok URL ────────────────────────────────────
log "Step 4: Updating .env with ngrok URL..."
WEBHOOK_URL="$NGROK_URL/vapi/webhook"

# Update backend .env
if grep -q "SERVER_URL=" "$DIR/.env"; then
    sed -i '' "s|SERVER_URL=.*|SERVER_URL=$WEBHOOK_URL|" "$DIR/.env"
else
    echo "SERVER_URL=$WEBHOOK_URL" >> "$DIR/.env"
fi
ok "Backend .env updated: SERVER_URL=$WEBHOOK_URL"

# Update frontend .env with backend URL
if grep -q "VITE_BACKEND_URL=" "$DIR/frontend/.env"; then
    sed -i '' "s|VITE_BACKEND_URL=.*|VITE_BACKEND_URL=$NGROK_URL|" "$DIR/frontend/.env"
else
    echo "VITE_BACKEND_URL=$NGROK_URL" >> "$DIR/frontend/.env"
fi
ok "Frontend .env updated: VITE_BACKEND_URL=$NGROK_URL"

# ─── Step 5: Test backend via ngrok ────────────────────────────────────────
log "Step 5: Testing backend through ngrok tunnel..."

HEALTH=$(curl -s "$NGROK_URL/health")
if echo "$HEALTH" | grep -q '"ok"'; then
    ok "Backend reachable through ngrok"
else
    fail "Backend not reachable through ngrok"
    cleanup
fi

# Test a sample VAPI webhook call through ngrok
QUERY_RESULT=$(curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "toolCallList": [{
        "id": "test_001",
        "name": "query_analytics",
        "arguments": {
          "sql_query": "SELECT SUM(dau) as total_dau FROM daily_metrics WHERE date >= '\''2026-02-02'\''",
          "query_description": "Total DAU for current week"
        }
      }],
      "call": { "id": "test_call" }
    }
  }')

if echo "$QUERY_RESULT" | grep -q "total_dau"; then
    ok "Webhook function call works through ngrok"
else
    fail "Webhook function call failed: $QUERY_RESULT"
fi

# ─── Step 6: Create VAPI assistant ─────────────────────────────────────────
log "Step 6: Creating VAPI assistant..."
python3 "$DIR/setup_vapi.py"

if [ -f "$DIR/vapi_config.json" ]; then
    ASSISTANT_ID=$(python3 -c "import json; print(json.load(open('$DIR/vapi_config.json'))['assistant_id'])")
    ok "Assistant created: $ASSISTANT_ID"

    # Update frontend .env with assistant ID
    if grep -q "VITE_VAPI_ASSISTANT_ID=" "$DIR/frontend/.env"; then
        sed -i '' "s|VITE_VAPI_ASSISTANT_ID=.*|VITE_VAPI_ASSISTANT_ID=$ASSISTANT_ID|" "$DIR/frontend/.env"
    else
        echo "VITE_VAPI_ASSISTANT_ID=$ASSISTANT_ID" >> "$DIR/frontend/.env"
    fi
    ok "Frontend .env updated with assistant ID"
else
    fail "VAPI assistant creation failed"
    cleanup
fi

# ─── Step 7: Start frontend ────────────────────────────────────────────────
log "Step 7: Starting frontend on port 5173..."
cd "$DIR/frontend"
npx vite --host &
FRONTEND_PID=$!
cd "$DIR"
sleep 3
ok "Frontend running at http://localhost:5173"

# ─── Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  E2E TEST ENVIRONMENT READY${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Frontend:     ${CYAN}http://localhost:5173${NC}"
echo -e "  Backend:      ${CYAN}http://localhost:8000${NC}"
echo -e "  ngrok tunnel: ${CYAN}$NGROK_URL${NC}"
echo -e "  Webhook URL:  ${CYAN}$WEBHOOK_URL${NC}"
echo -e "  Assistant ID: ${CYAN}$ASSISTANT_ID${NC}"
echo ""
echo -e "  ${YELLOW}Open http://localhost:5173 in your browser and tap the mic!${NC}"
echo ""
echo -e "  Press Ctrl+C to shut everything down."
echo ""

# Keep alive
wait

# Voice-to-Data: Executive Analytics Agent

A real-time voice agent that lets executives ask business questions in natural English. Ask a question out loud, get a spoken answer with a visual comparison table on screen.

**Demo:** CPO says "Why did product engagement drop last week?" → Agent asks a clarifier → Speaks the top 3 reasons → Shows a before/after comparison table.

## Tech Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| Voice Interface | [VAPI](https://vapi.ai) | Speech-to-text, text-to-speech, function calling |
| LLM | GPT-4o (via VAPI) | Natural language → SQL, answer synthesis |
| Frontend | React + Vite + Tailwind | Chat transcript + comparison table UI |
| Backend | FastAPI (Python) | Webhook handler, SQL execution, SSE streaming |
| Data Layer | SQLite | 9-table synthetic analytics database |
| Tunnel | ngrok | Exposes local backend to VAPI's servers |

## Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **ngrok** — [sign up](https://ngrok.com) and authenticate
- **VAPI account** — get API keys from [vapi.ai dashboard](https://dashboard.vapi.ai)

## Quick Start

### 1. Install dependencies

```bash
# Backend
pip3 install fastapi uvicorn

# Frontend
cd frontend && npm install && cd ..

# ngrok (macOS)
brew install ngrok
ngrok config add-authtoken <your-ngrok-token>
```

### 2. Generate the dataset

```bash
python3 generate_data.py
```

This creates `engagement.db` with 13,440 rows across 9 tables.

### 3. Configure environment

```bash
# Backend config
cp .env.example .env
# Edit .env → set VAPI_API_KEY (Private API Key from VAPI dashboard)

# Frontend config
cp frontend/.env.example frontend/.env
# Edit frontend/.env → set VITE_VAPI_PUBLIC_KEY (Public Key from VAPI dashboard)
```

### 4. Run everything (automated)

```bash
./test_e2e.sh
```

This script:
1. Starts the backend on port 8000
2. Opens an ngrok tunnel
3. Creates the VAPI assistant + tools
4. Starts the frontend on port 5173
5. Prints all URLs

### 4b. Run manually (step by step)

```bash
# Terminal 1: Backend
python3 server.py

# Terminal 2: ngrok tunnel
ngrok http 8000
# Copy the https URL

# Terminal 3: Setup VAPI (update .env with ngrok URL first)
python3 setup_vapi.py
# Copy the assistant ID into frontend/.env as VITE_VAPI_ASSISTANT_ID

# Terminal 4: Frontend
cd frontend && npm run dev
```

### 5. Use it

Open **http://localhost:5173** in your browser. Tap the mic button and ask a question.

## Sample Questions

### Product Engagement
- "Why did product engagement drop last week?"
- "What happened to mobile session duration?"
- "Which features have the worst drop-off rates?"
- "Show me DAU trends by platform"

### Revenue & Churn
- "How is our revenue doing?"
- "Show me churn by segment"
- "What's our net revenue retention?"
- "Which segment has the highest churned MRR?"

### Acquisition
- "What's our acquisition cost by channel?"
- "How is our LTV to CAC ratio?"
- "Which channels are driving the most signups?"
- "Is mobile acquisition getting more expensive?"

### Support & NPS
- "Are support tickets increasing?"
- "What's our NPS score?"
- "Which ticket category has the longest resolution time?"
- "How is customer satisfaction trending?"

### Geographic
- "How is Asia Pacific performing?"
- "Show me churn rates by region"
- "Which region has the best engagement?"

## Project Structure

```
Voice-2-Data/
├── server.py              # FastAPI backend — VAPI webhook handler + SSE
├── generate_data.py       # Synthetic dataset generator (9 tables)
├── setup_vapi.py          # Creates VAPI assistant + tools via API
├── test_e2e.sh            # One-command E2E launcher
├── engagement.db          # SQLite database (generated)
├── vapi_config.json       # VAPI resource IDs (generated)
├── .env                   # Backend config (VAPI_API_KEY, SERVER_URL)
├── PRD.md                 # Product Requirements Document
├── LOVABLE_PROMPT.md      # Alternative: paste into lovable.dev
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # Main layout
│   │   ├── hooks/useVapi.ts           # VAPI Web SDK integration
│   │   ├── hooks/useTableStream.ts    # SSE for live table updates
│   │   ├── hooks/useAuth.tsx          # Google auth context + JWT validation
│   │   ├── components/
│   │   │   ├── LoginScreen.tsx        # Google Sign-In login page
│   │   │   ├── ConversationPanel.tsx   # Chat transcript
│   │   │   ├── ComparisonTable.tsx     # Before/after data table
│   │   │   ├── MicButton.tsx           # Mic button with animations
│   │   │   └── StatusIndicator.tsx     # Listening/Thinking/Speaking
│   │   └── index.css                  # Tailwind + custom styles
│   ├── .env                           # Frontend config (VAPI keys)
│   └── package.json
```

## Database Schema

| Table | Rows | Key Metrics |
|-------|------|-------------|
| `daily_metrics` | 504 | DAU, WAU, MAU, session duration, bounce rate, pages/session |
| `feature_usage` | 5,040 | Adoption rate, sessions, drop-off rate, time in feature |
| `funnel_metrics` | 2,016 | Conversion rate, user count per funnel step |
| `revenue` | 168 | MRR, ARR, new/churned/expansion MRR, ARPU |
| `churn` | 504 | Churn rate, churned users, NRR, GRR |
| `acquisition` | 1,008 | Signups, CAC, LTV, LTV/CAC ratio, spend |
| `support_tickets` | 3,024 | Tickets opened/resolved, resolution hours, CSAT |
| `nps_scores` | 504 | NPS score, promoter/passive/detractor % |
| `geo_metrics` | 672 | Regional DAU, revenue, churn, session duration |

## Architecture

```
[Executive Voice]
    → VAPI (Speech-to-Text)
    → GPT-4o (intent understanding + SQL generation)
    → Function Call → FastAPI backend
    → SQLite query execution
    → Results → GPT-4o (answer synthesis)
    → VAPI (Text-to-Speech) + SSE → Frontend (comparison table)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/vapi/webhook` | POST | VAPI webhook handler (tool-calls) |
| `/api/table/{call_id}` | GET | Get latest comparison table |
| `/api/table-stream/{call_id}` | GET | SSE stream for live table updates |
| `/api/schema` | GET | Database schema |
| `/health` | GET | Health check |

## Authentication

Google Sign-In is enforced on both frontend and backend.

**Frontend:** `@react-oauth/google` gates the app behind a login screen. The Google JWT is stored in `sessionStorage` and sent with every API request.

**Backend:** All `/api/*` endpoints require a valid Google JWT. The server verifies tokens against Google's `tokeninfo` endpoint (full signature + claims verification, cached in-memory). Set `GOOGLE_CLIENT_ID` in `.env` to restrict tokens to your app's audience.

| Endpoint | Auth |
|---|---|
| `/api/*` | Google JWT required (`Authorization: Bearer` header) |
| `/vapi/webhook` | `x-vapi-secret` header (set `VAPI_WEBHOOK_SECRET` in `.env`) |
| `/health` | Public |

The webhook secret is configured in both the backend `.env` and the VAPI assistant's `server.secret` (set via `setup_vapi.py` or the VAPI dashboard). VAPI sends the `x-vapi-secret` header on every webhook call; the backend verifies it with constant-time comparison.

## Real Data Ingestion (REES46 + GA)

This repo includes a stdlib-only ingester that loads large real datasets into the existing SQLite schema (no schema changes required).

### Expected files (CSV or CSV.gz)

- REES46 multi-category events: `rees46_events.csv`
  - Must include: `event_time`, `event_type`, `user_id`, `user_session`
  - Optional: `category_code`, `brand`, `product_id`, `price`, `country`

- GA revenue prediction sessions: `ga_sessions.csv`
  - Must include: `date` (YYYYMMDD) and `fullVisitorId`
  - Optional (any format): `visitId`, `device.deviceCategory`, `geoNetwork.country`,
    `trafficSource.medium`, `trafficSource.source`, `totals.pageviews`, `totals.timeOnSite`,
    `totals.transactions`, `totals.transactionRevenue`

### Run ingest

Place the CSVs in the repo root and run:

```bash
python3 ingest_real_data.py \
  --db ./engagement.db \
  --rees46 ./rees46_events.csv \
  --ga ./ga_sessions.csv \
  --reset
```

Options:
- `--limit 100000` to cap rows per dataset
- `.csv.gz` inputs are supported

## Voice Behavior

The assistant uses VAPI's `stopSpeakingPlan` to support **barge-in** — when the user starts speaking, the agent immediately stops talking:

| Setting | Value | Effect |
|---------|-------|--------|
| `numWords` | 0 | Stop on any speech (no minimum word count) |
| `voiceSeconds` | 0.2 | 200ms of detected voice triggers the stop |
| `backoffSeconds` | 1 | Wait 1s before resuming after interruption |

This is configured in `setup_vapi.py` and applied to the VAPI assistant via API.

## Testing

```bash
# Backend (45 tests)
source .venv/bin/activate && python -m pytest tests/ -v

# Frontend (31 tests)
cd frontend && npm test
```

## Troubleshooting

**"No data" responses:** The LLM may generate SQL with wrong column names. Check backend logs for the actual SQL being generated.

**ngrok tunnel expired:** Free ngrok tunnels expire. Restart ngrok, update `.env`, and re-run `setup_vapi.py`.

**VAPI 403 error:** Ensure your API key is valid. Check the VAPI dashboard for usage limits.

**Port in use:** Run `lsof -ti:8000 | xargs kill -9` and `lsof -ti:5173 | xargs kill -9`.

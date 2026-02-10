"""
Backend function handler for VAPI Voice-to-Data agent.

Handles VAPI webhook events (tool-calls) and provides:
- query_analytics: Execute SQL against engagement.db
- display_comparison_table: Push table data to frontend via SSE
"""

import asyncio
import json
import logging
import os
import re
import secrets
import sqlite3
import time
import urllib.request
import urllib.error
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-to-data")

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse


# ── Load .env file ─────────────────────────────────────────────────────────

def _load_env_file():
    """Load .env file into os.environ (no python-dotenv dependency)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip()
                if key not in os.environ:  # Don't override real env vars
                    os.environ[key] = val

_load_env_file()

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(title="Voice-to-Data Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engagement.db")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
VAPI_WEBHOOK_SECRET = os.environ.get("VAPI_WEBHOOK_SECRET", "")

# In-memory store for comparison tables, keyed by call_id
# Frontend polls/SSE subscribes to get the latest table for a session
table_store: dict[str, dict] = {}
# SSE event queues per call_id
sse_queues: dict[str, list[asyncio.Queue]] = {}

# ── Google JWT Verification ────────────────────────────────────────────────

# Cache verified tokens: token -> (email, exp_time)
_token_cache: dict[str, tuple[str, float]] = {}
_CACHE_MAX = 500


def _verify_google_token(token: str) -> dict:
    """Verify a Google ID token using Google's tokeninfo endpoint.

    Returns the token payload on success, raises HTTPException on failure.
    This fully verifies the JWT signature, issuer, audience, and expiry
    on Google's servers — no cryptography library needed.
    """
    # Check cache first
    now = time.time()
    if token in _token_cache:
        email, exp = _token_cache[token]
        if exp > now:
            return {"email": email}
        else:
            del _token_cache[token]

    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            payload = json.loads(resp.read())
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as e:
        logger.warning(f"Google token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Verify audience matches our client ID
    if GOOGLE_CLIENT_ID and payload.get("aud") != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=401, detail="Token audience mismatch")

    # Cache the verified token
    exp = float(payload.get("exp", 0))
    email = payload.get("email", "")
    if len(_token_cache) >= _CACHE_MAX:
        _token_cache.clear()
    _token_cache[token] = (email, exp)

    return payload


def require_auth(request: Request) -> dict:
    """FastAPI dependency: extract and verify Google JWT from Authorization header."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")

    token = auth_header[7:]
    return _verify_google_token(token)


# ── VAPI Webhook Auth ──────────────────────────────────────────────────────

def require_vapi_secret(request: Request) -> None:
    """Verify the x-vapi-secret header if VAPI_WEBHOOK_SECRET is configured."""
    if not VAPI_WEBHOOK_SECRET:
        return  # No secret configured, skip check
    header_secret = request.headers.get("x-vapi-secret", "")
    if not secrets.compare_digest(header_secret, VAPI_WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid webhook secret")


# ── SQL Safety ──────────────────────────────────────────────────────────────

BLOCKED_PATTERNS = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> str | None:
    """Return an error message if SQL is unsafe, else None."""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        return "Only SELECT queries are allowed."
    if BLOCKED_PATTERNS.search(sql):
        return "Query contains a blocked keyword."
    if ";" in stripped:
        return "Multiple statements are not allowed."
    return None


# ── Database ────────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def execute_query(sql: str) -> dict:
    """Execute a read-only SQL query and return results."""
    error = validate_sql(sql)
    if error:
        return {"error": error}

    try:
        with get_db() as conn:
            cursor = conn.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = [dict(row) for row in cursor.fetchall()]
            return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except sqlite3.Error as e:
        return {"error": f"SQL error: {e}"}


# ── Tool Handlers ───────────────────────────────────────────────────────────

def handle_query_analytics(args: dict, call_id: str) -> str:
    sql = args.get("sql_query", "")
    description = args.get("query_description", "")

    logger.info(f"[{call_id}] QUERY: {description}")
    logger.info(f"[{call_id}] SQL: {sql}")

    result = execute_query(sql)

    if "error" in result:
        logger.warning(f"[{call_id}] ERROR: {result['error']}")
        return f"Query failed: {result['error']}"

    # Format results as a readable string for the LLM
    if result["row_count"] == 0:
        return "The query returned no results."

    # Cap at 50 rows to keep the response manageable
    rows = result["rows"][:50]
    columns = result["columns"]

    # Build a text table
    lines = [f"Query: {description}", f"Results ({result['row_count']} rows):"]
    lines.append(" | ".join(columns))
    lines.append("-" * len(lines[-1]))
    for row in rows:
        lines.append(" | ".join(str(row.get(c, "")) for c in columns))

    result_str = " ".join(lines)
    logger.info(f"[{call_id}] RESULT: {result['row_count']} rows returned")
    return result_str


def handle_display_comparison_table(args: dict, call_id: str) -> str:
    table_data = {
        "title": args.get("title", "Comparison"),
        "columns": args.get("columns", []),
        "rows": args.get("rows", []),
        "timestamp": time.time(),
    }

    # Store for polling endpoint
    table_store[call_id] = table_data

    # Push to SSE subscribers
    if call_id in sse_queues:
        for queue in sse_queues[call_id]:
            queue.put_nowait(table_data)

    return "Comparison table displayed on screen."


TOOL_HANDLERS = {
    "query_analytics": handle_query_analytics,
    "display_comparison_table": handle_display_comparison_table,
}

# ── VAPI Webhook (secret-protected) ────────────────────────────────────────

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request, _: None = Depends(require_vapi_secret)):
    body = await request.json()
    message = body.get("message", {})
    msg_type = message.get("type", "")

    # Only handle tool-calls; acknowledge everything else
    if msg_type != "tool-calls":
        logger.info(f"Webhook event: {msg_type}")
        return {}

    call_id = message.get("call", {}).get("id", "unknown")
    tool_call_list = message.get("toolCallList", [])

    results = []
    for tool_call in tool_call_list:
        tc_id = tool_call.get("id", "")
        # VAPI sends tool calls in OpenAI format: {function: {name, arguments}}
        func = tool_call.get("function", {})
        tc_name = func.get("name", "") or tool_call.get("name", "")
        tc_args = func.get("arguments", {}) or tool_call.get("arguments", {})
        # arguments may be a JSON string — parse it
        if isinstance(tc_args, str):
            try:
                tc_args = json.loads(tc_args)
            except (json.JSONDecodeError, ValueError):
                tc_args = {}

        handler = TOOL_HANDLERS.get(tc_name)
        if handler:
            result_str = handler(tc_args, call_id)
        else:
            result_str = f"Unknown function: {tc_name}"

        results.append({"toolCallId": tc_id, "result": result_str})

    return {"results": results}


# ── Frontend Endpoints (auth required) ─────────────────────────────────────

@app.get("/api/table/{call_id}")
async def get_table(call_id: str, _user: dict = Depends(require_auth)):
    """Polling endpoint: get the latest comparison table for a call."""
    data = table_store.get(call_id)
    if data:
        return data
    return {"title": None, "columns": [], "rows": []}


@app.get("/api/table-stream/{call_id}")
async def table_stream(call_id: str, _user: dict = Depends(require_auth)):
    """SSE endpoint: stream comparison table updates for a call."""
    queue: asyncio.Queue = asyncio.Queue()

    if call_id not in sse_queues:
        sse_queues[call_id] = []
    sse_queues[call_id].append(queue)

    async def event_generator():
        try:
            # Send current table if one exists
            if call_id in table_store:
                yield f"data: {json.dumps(table_store[call_id])}\n\n"

            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            if call_id in sse_queues:
                sse_queues[call_id].remove(queue)
                if not sse_queues[call_id]:
                    del sse_queues[call_id]

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/schema")
async def get_schema(_user: dict = Depends(require_auth)):
    """Return the database schema (useful for debugging/frontend display)."""
    with get_db() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()

        schema = {}
        for table in tables:
            name = table["name"]
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            schema[name] = [{"name": c["name"], "type": c["type"]} for c in cols]

    return schema


# ── Public Endpoints ───────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "db_exists": os.path.exists(DB_PATH)}


@app.on_event("startup")
async def startup_warnings():
    if not GOOGLE_CLIENT_ID:
        logger.warning(
            "GOOGLE_CLIENT_ID not set — /api/* auth will accept any valid Google token. "
            "Set it in .env to restrict to your app's audience."
        )
    if not VAPI_WEBHOOK_SECRET:
        logger.warning(
            "VAPI_WEBHOOK_SECRET not set — /vapi/webhook is open to anyone. "
            "Set it in .env and configure server.secret in VAPI to protect it."
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

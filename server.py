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
import sqlite3
import time
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("voice-to-data")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI(title="Voice-to-Data Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engagement.db")

# In-memory store for comparison tables, keyed by call_id
# Frontend polls/SSE subscribes to get the latest table for a session
table_store: dict[str, dict] = {}
# SSE event queues per call_id
sse_queues: dict[str, list[asyncio.Queue]] = {}

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

# ── VAPI Webhook ────────────────────────────────────────────────────────────

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
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
        tc_name = tool_call.get("name", "")
        tc_args = tool_call.get("arguments", {})

        handler = TOOL_HANDLERS.get(tc_name)
        if handler:
            result_str = handler(tc_args, call_id)
        else:
            result_str = f"Unknown function: {tc_name}"

        results.append({"toolCallId": tc_id, "result": result_str})

    return {"results": results}


# ── Frontend Endpoints ──────────────────────────────────────────────────────

@app.get("/api/table/{call_id}")
async def get_table(call_id: str):
    """Polling endpoint: get the latest comparison table for a call."""
    data = table_store.get(call_id)
    if data:
        return data
    return {"title": None, "columns": [], "rows": []}


@app.get("/api/table-stream/{call_id}")
async def table_stream(call_id: str):
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
async def get_schema():
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


@app.get("/health")
async def health():
    return {"status": "ok", "db_exists": os.path.exists(DB_PATH)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

"""
Setup script: creates VAPI tools and assistant via the VAPI API.

Usage:
  1. Copy .env.example to .env and fill in your VAPI_API_KEY and SERVER_URL
  2. Run: python3 setup_vapi.py
  3. It prints the assistant ID — use this in the frontend to start calls

Prerequisites:
  - Expose your local server with: ngrok http 8000
  - Set SERVER_URL in .env to: https://<your-id>.ngrok-free.app/vapi/webhook
"""

import json
import os
import sys
import urllib.request
import urllib.error

# ── Load config ─────────────────────────────────────────────────────────────

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        print("ERROR: .env file not found. Copy .env.example to .env and fill in your values.")
        sys.exit(1)
    env = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                env[key.strip()] = val.strip()
    return env


env = load_env()
API_KEY = env.get("VAPI_API_KEY", "")
SERVER_URL = env.get("SERVER_URL", "")
WEBHOOK_SECRET = env.get("VAPI_WEBHOOK_SECRET", "")

if not API_KEY or API_KEY == "your-vapi-api-key-here":
    print("ERROR: Set VAPI_API_KEY in .env")
    sys.exit(1)
if not SERVER_URL or "your-ngrok-url" in SERVER_URL:
    print("ERROR: Set SERVER_URL in .env (run ngrok http 8000 first)")
    sys.exit(1)
if not WEBHOOK_SECRET or WEBHOOK_SECRET == "your-webhook-secret-here":
    print("WARNING: VAPI_WEBHOOK_SECRET not set in .env — webhook will be unprotected.")

VAPI_BASE = "https://api.vapi.ai"

# Build server config (shared by tools and assistant)
SERVER_CONFIG: dict = {"url": SERVER_URL, "timeoutSeconds": 20}
if WEBHOOK_SECRET:
    SERVER_CONFIG["secret"] = WEBHOOK_SECRET

# ── API helpers ─────────────────────────────────────────────────────────────

def vapi_post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{VAPI_BASE}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Voice-to-Data/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"API error {e.code}: {body}")
        sys.exit(1)

# ── Tool definitions ────────────────────────────────────────────────────────

QUERY_ANALYTICS_TOOL = {
    "type": "function",
    "function": {
        "name": "query_analytics",
        "description": (
            "Execute a SQL query against the product engagement database. "
            "Use this to answer questions about DAU, WAU, MAU, session duration, "
            "feature adoption, drop-off rates, and funnel conversion rates. "
            "Always use week-over-week comparisons when investigating changes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": "A read-only SELECT SQL query to execute against the SQLite database.",
                },
                "query_description": {
                    "type": "string",
                    "description": "A short human-readable description of what this query checks.",
                },
            },
            "required": ["sql_query", "query_description"],
        },
    },
    "server": SERVER_CONFIG,
    "messages": [
        {"type": "request-failed", "content": "I had trouble querying the data. Let me try a different approach."},
        {"type": "request-response-delayed", "content": "Still crunching the numbers, one moment."},
    ],
}

DISPLAY_TABLE_TOOL = {
    "type": "function",
    "function": {
        "name": "display_comparison_table",
        "description": (
            "Display a comparison table on the executive's screen. "
            "Call this AFTER you have query results to show a visual before/after breakdown. "
            "Mark the top contributing factors with is_top_contributor: true."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title for the comparison table.",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column header names.",
                },
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dimension": {"type": "string"},
                            "previous_value": {"type": "string"},
                            "current_value": {"type": "string"},
                            "delta": {"type": "string"},
                            "is_top_contributor": {"type": "boolean"},
                        },
                    },
                    "description": "Rows of comparison data.",
                },
            },
            "required": ["title", "columns", "rows"],
        },
    },
    "server": SERVER_CONFIG,
    "messages": [
        {"type": "request-start", "content": "Putting the breakdown on your screen now."},
        {"type": "request-failed", "content": "I couldn't display the table, but I'll summarize verbally."},
    ],
}

# ── System prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an executive analytics assistant with access to a comprehensive business analytics database.
You help CPOs, CEOs, and VPs understand their metrics by answering questions in clear, executive-friendly language.

DATABASE SCHEMA (9 tables):

1. daily_metrics (date TEXT, platform TEXT, segment TEXT, dau INTEGER, wau INTEGER, mau INTEGER, session_duration_avg REAL, sessions_per_user REAL, bounce_rate REAL, pages_per_session REAL)
2. feature_usage (date TEXT, feature_name TEXT, platform TEXT, segment TEXT, adoption_rate REAL, sessions_with_feature INTEGER, drop_off_rate REAL, avg_time_in_feature REAL)
3. funnel_metrics (date TEXT, funnel_step TEXT, platform TEXT, segment TEXT, conversion_rate REAL, users_count INTEGER)
4. revenue (date TEXT, segment TEXT, mrr REAL, arr REAL, new_mrr REAL, churned_mrr REAL, expansion_mrr REAL, paying_customers INTEGER, arpu REAL)
5. churn (date TEXT, segment TEXT, platform TEXT, churn_rate REAL, churned_users INTEGER, net_revenue_retention REAL, gross_revenue_retention REAL)
6. acquisition (date TEXT, channel TEXT, platform TEXT, new_signups INTEGER, cac REAL, ltv REAL, ltv_cac_ratio REAL, spend REAL)
7. support_tickets (date TEXT, category TEXT, segment TEXT, platform TEXT, tickets_opened INTEGER, tickets_resolved INTEGER, avg_resolution_hours REAL, csat_score REAL)
8. nps_scores (date TEXT, segment TEXT, platform TEXT, nps_score INTEGER, promoters_pct REAL, passives_pct REAL, detractors_pct REAL, responses INTEGER)
9. geo_metrics (date TEXT, region TEXT, segment TEXT, dau INTEGER, revenue REAL, churn_rate REAL, avg_session_duration REAL)

VALID VALUES:
- platform: 'web', 'mobile', 'tablet'
- segment: 'free', 'pro', 'enterprise'
- feature_name: 'Feature X', 'Feature Y', 'Feature Z', 'Search', 'Dashboard', 'Export', 'Notifications', 'Analytics', 'Integrations', 'API'
- funnel_step: 'signup', 'onboarding', 'activation', 'retention'
- channel: 'organic', 'paid_search', 'paid_social', 'referral', 'email', 'direct'
- region: 'north_america', 'europe', 'asia_pacific', 'latin_america'
- category (support): 'bug', 'feature_request', 'billing', 'onboarding_help', 'performance', 'account'
- date range: 2025-12-15 to 2026-02-08 (8 weeks of daily data)
- current week: 2026-02-02 to 2026-02-08
- previous week: 2026-01-26 to 2026-02-01

BEHAVIOR RULES:
1. If the user's question is specific enough, call query_analytics immediately.
2. If the question is vague or could benefit from narrowing, ask ONE short clarifying question before querying.
3. NEVER show SQL to the user. Speak in plain business language.
4. You may call query_analytics MULTIPLE times to investigate different angles.
5. After gathering data, lead with the #1 finding, then list 2-3 contributing factors ranked by impact.
6. ALWAYS call display_comparison_table after presenting findings to show the data visually on screen.
7. Keep spoken responses under 60 seconds. Be concise and direct.
8. You have data on engagement, revenue, churn, acquisition, support, NPS, features, funnels, and geography. If asked about something truly outside this scope, say so and suggest what you CAN answer.

SQL TIPS:
- Use CASE WHEN date >= '2026-02-02' THEN 'current_week' ELSE 'previous_week' END for week-over-week comparisons
- Always filter date >= '2026-01-26' for week-over-week comparisons
- Use ROUND() for clean numbers
- Use GROUP BY and ORDER BY to rank dimensions
- For revenue questions, query the revenue table (mrr, arr, churned_mrr, new_mrr, expansion_mrr, arpu)
- For churn questions, query the churn table (churn_rate, churned_users, net_revenue_retention, gross_revenue_retention)
- For acquisition questions, query the acquisition table (new_signups, cac, ltv, ltv_cac_ratio, spend by channel)
- For support questions, query support_tickets (tickets_opened, tickets_resolved, avg_resolution_hours, csat_score)
- For NPS questions, query nps_scores (nps_score, promoters_pct, detractors_pct)
- For geographic questions, query geo_metrics (dau, revenue, churn_rate by region)

EXAMPLE INTERACTIONS:

Example 1 - Engagement:
User: "Why did engagement drop last week?"
You: "Are you asking about all platforms, or a specific one like mobile or web?"
User: "All platforms."
[Call query_analytics multiple times to investigate]
You: "The overall engagement dip of about 3% was mainly driven by three things. First, mobile session duration dropped nearly 8%, likely tied to a recent app update. Second, onboarding completion in the free tier fell about 12%. And third, Feature X adoption declined around 5% week over week. I've put the full comparison on your screen."
[Call display_comparison_table]

Example 2 - Revenue:
User: "How is our revenue doing?"
[Call query_analytics: SELECT segment, ROUND(AVG(mrr),0) as avg_mrr, ROUND(AVG(churned_mrr),0) as avg_churned FROM revenue WHERE date >= '2026-01-26' GROUP BY segment]
You: "Total MRR across paid segments is around 805K. However, enterprise churned MRR has spiked 45% this week, with average daily churn at about 15K, up from 10K last week. Pro segment new MRR is also down about 10%."
[Call display_comparison_table]

Example 3 - Churn:
User: "Show me churn by segment"
[Call query_analytics on churn table with week-over-week by segment]
You: "Enterprise churn rate jumped 40% this week to about 2.1%, up from 1.5%. Free tier mobile churn is also up 15%. Pro segment remains stable at around 3%."
[Call display_comparison_table]"""

# ── Create everything ───────────────────────────────────────────────────────

def main():
    print("Creating VAPI tools...")

    # Create tools
    tool1 = vapi_post("/tool", QUERY_ANALYTICS_TOOL)
    tool1_id = tool1["id"]
    print(f"  query_analytics tool:        {tool1_id}")

    tool2 = vapi_post("/tool", DISPLAY_TABLE_TOOL)
    tool2_id = tool2["id"]
    print(f"  display_comparison_table tool: {tool2_id}")

    print("\nCreating VAPI assistant...")

    assistant = vapi_post("/assistant", {
        "name": "Voice-to-Data Analytics Agent",
        "firstMessage": (
            "Good morning. I'm your product analytics assistant. "
            "You can ask me about engagement metrics, feature adoption, "
            "conversion funnels, and more. What would you like to know?"
        ),
        "firstMessageMode": "assistant-speaks-first",
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "temperature": 0.3,
            "maxTokens": 1024,
            "toolIds": [tool1_id, tool2_id],
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "pNInz6obpgDQGcFmaJgB",  # "Adam" - professional male voice
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en",
        },
        "server": {
            "url": SERVER_URL,
            "timeoutSeconds": 20,
        },
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600,
        "endCallMessage": "Thanks for the chat. Have a great day.",
    })

    assistant_id = assistant["id"]
    print(f"  Assistant created:            {assistant_id}")

    # Save IDs for the frontend
    config = {
        "assistant_id": assistant_id,
        "tool_ids": {
            "query_analytics": tool1_id,
            "display_comparison_table": tool2_id,
        },
        "server_url": SERVER_URL,
    }
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vapi_config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\nConfig saved to: {config_path}")
    print(f"\n{'='*50}")
    print(f"ASSISTANT ID: {assistant_id}")
    print(f"{'='*50}")
    print(f"\nUse this ID in your Lovable frontend to start voice calls.")
    print(f"Your webhook URL: {SERVER_URL}")


if __name__ == "__main__":
    main()

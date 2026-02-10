# PRD: Voice-to-Data Executive Analytics Agent

**Version:** 1.0
**Author:** Manoj Mohan
**Date:** 2026-02-09
**Status:** Draft — Hackathon MVP
**Time Budget:** 2 hours

---

## 1. Problem Statement

Executives (CPO, CEO, VP) need quick answers to business questions but are bottlenecked by:
- Waiting for analyst teams to pull data
- Navigating complex BI dashboards
- Context-switching from meetings to tools

They want to **ask a question out loud** and **get an answer in seconds** — with supporting data on screen.

---

## 2. Product Vision

A real-time voice agent that lets executives ask business questions in natural English. The agent listens, understands intent, queries analytics data, identifies root causes, and responds with a spoken summary + visual comparison table.

**Demo Moment:** Executive says "Why did product engagement drop last week?" → Agent asks a smart clarifier → Speaks the top reasons → Shows a before/after comparison table on screen.

---

## 3. Target User

**Primary Persona:** CPO (Chief Product Officer)
- Asks product engagement questions
- Wants fast, high-level answers with option to drill down
- Non-technical — should never see SQL or raw data

**Demo Scenario (Happy Path):**
> CPO: "Why did product engagement drop by 2% last week?"
> Agent: "Just to narrow it down — are you asking about all platforms or a specific one like mobile or web?"
> CPO: "All platforms."
> Agent: "Got it. The 2% drop was primarily driven by three factors. First, mobile session duration decreased 8% after the app update on Tuesday. Second, the onboarding completion rate dropped 12% in the free tier segment. Third, feature X adoption fell 5% week-over-week. I've put a comparison table on your screen."
> [Screen shows before/after comparison table]

---

## 4. Tech Stack

| Component | Tool | Role |
|-----------|------|------|
| Voice Interface | **VAPI** | Speech-to-text, text-to-speech, function calling mid-conversation |
| LLM | **VAPI-supported LLM** (GPT-4o or equivalent) | Natural language understanding, SQL generation, answer synthesis |
| Frontend | **Lovable** | Chat + chart hybrid UI, visual comparison tables |
| Session State | **Hathora** | Real-time per-user session state (conversation context, active query, filters) |
| Data Layer | **SQLite + Public Dataset** | Mock analytics warehouse with product engagement metrics |

---

## 5. Architecture Overview

```
[Executive Voice]
    → VAPI (STT)
    → LLM (intent + clarification logic)
    → Function Call (query generation)
    → SQLite (data retrieval)
    → LLM (answer synthesis)
    → VAPI (TTS) + Lovable (comparison table)

Hathora manages session state throughout:
    - Conversation history
    - Active filters/context
    - Query results cache
```

### Data Flow (Step-by-Step)

1. **User speaks** → VAPI captures audio, converts to text
2. **VAPI sends text to LLM** with system prompt + schema context
3. **LLM evaluates ambiguity:**
   - Clear question → generates SQL directly
   - Vague question → returns a clarifying question (via VAPI function call)
4. **VAPI function call** triggers backend to execute SQL against SQLite
5. **Results returned to LLM** → synthesizes spoken summary (top 2-3 reasons, ranked)
6. **VAPI speaks the answer** (TTS)
7. **Frontend (Lovable)** receives results via Hathora session → renders comparison table
8. **Hathora** persists session state for potential follow-ups

---

## 6. Features — MVP (2-Hour Build)

### F1: Voice Input (VAPI STT)
- User taps a "Start" button on the web page
- VAPI captures microphone audio and converts to text
- No authentication required — direct URL access
- Single mic button, zero-friction start

### F2: Smart Adaptive Clarification
- LLM receives the transcribed question + data schema context
- **If the question is specific enough** (e.g., "Why did DAU drop last week?") → answer directly
- **If the question is vague** (e.g., "How are things going?") → ask 1 targeted clarifying question via voice
- Clarification examples:
  - "Which time period are you asking about?"
  - "Are you asking about all platforms or a specific one?"
  - "Do you want to focus on a particular user segment?"
- After clarification, proceed to answer

### F3: Natural Language to SQL
- LLM generates SQL query based on:
  - User's question (transcribed text)
  - Pre-loaded schema description (table names, columns, relationships)
  - System prompt with few-shot examples
- SQL targets a SQLite database loaded with the public dataset
- **VAPI function calling** is the mechanism: LLM returns a function call → backend executes SQL → returns results

### F4: Answer Synthesis (Voice + Visual)
- LLM receives SQL results and synthesizes:
  - **Spoken answer** (via VAPI TTS): "The top 3 reasons for the drop are..." — concise, executive-friendly language
  - **Comparison table data** sent to frontend
- Answer format: ranked list of contributing factors with before/after values

### F5: Comparison Table (Lovable Frontend)
- Chat + chart hybrid layout:
  - **Left panel:** Conversation transcript (what user said, what agent said)
  - **Right panel:** Comparison table showing:
    - Dimension (e.g., platform, segment, feature)
    - Previous period value
    - Current period value
    - Delta (absolute + percentage)
    - Highlighted rows for top contributors to the change
- Table appears in real-time as the agent speaks

### F6: Session State (Hathora)
- Each user session gets a Hathora room
- Session stores:
  - Conversation history (user questions + agent answers)
  - Current active context (time period, filters applied)
  - Last query results
- Enables the frontend to stay in sync with the voice conversation
- State is transient — no persistence needed beyond the session

### F7: Scope Awareness
- When the user asks something outside the agent's data scope:
  - Agent responds: "I don't have data for that. I can help with product engagement metrics like DAU, session duration, feature adoption, and segment breakdowns."
  - Suggests a valid alternative query
- No silent failures — agent is always explicit about its limitations

---

## 7. Data Model

### Recommended Dataset
Use a **synthetic dataset** specifically crafted for the demo story. This guarantees the "engagement drop" narrative works perfectly and avoids wasting time finding/cleaning a public dataset.

### Schema: `product_engagement`

| Table | Columns | Description |
|-------|---------|-------------|
| `daily_metrics` | `date, platform (web/mobile/tablet), segment (free/pro/enterprise), dau, wau, mau, session_duration_avg, sessions_per_user` | Daily aggregated engagement metrics |
| `feature_usage` | `date, feature_name, platform, segment, adoption_rate, sessions_with_feature, drop_off_rate` | Feature-level engagement data |
| `funnel_metrics` | `date, funnel_step (signup/onboarding/activation/retention), platform, segment, conversion_rate, users_count` | Funnel conversion metrics |

### Data Requirements
- **Time range:** 8 weeks of daily data (enough for week-over-week comparison)
- **Built-in narrative:** Data must show a clear ~2% overall engagement drop in the most recent week, driven by:
  1. Mobile session duration decrease (~8%) after a simulated app update
  2. Free tier onboarding completion drop (~12%)
  3. Feature X adoption decline (~5%)
- **Volume:** ~3,000-5,000 rows total (small enough for SQLite, rich enough for drill-downs)

---

## 8. VAPI Configuration

### Assistant Setup
- **Model:** VAPI-supported LLM (GPT-4o recommended for function calling reliability)
- **Voice:** Professional, neutral tone (VAPI default or ElevenLabs if available)
- **System Prompt:** Includes:
  - Role: "You are an executive analytics assistant for product engagement data"
  - Schema description (all tables + columns)
  - Few-shot SQL examples (3-5 common queries)
  - Instructions for adaptive clarification logic
  - Answer format guidelines (concise, executive-friendly, ranked factors)

### Function Definitions
```json
{
  "name": "query_analytics",
  "description": "Execute a SQL query against the product engagement database and return results",
  "parameters": {
    "type": "object",
    "properties": {
      "sql_query": {
        "type": "string",
        "description": "The SQL query to execute against the SQLite database"
      },
      "query_description": {
        "type": "string",
        "description": "Human-readable description of what this query is checking"
      }
    },
    "required": ["sql_query", "query_description"]
  }
}
```

```json
{
  "name": "display_comparison_table",
  "description": "Send a comparison table to the frontend for visual display",
  "parameters": {
    "type": "object",
    "properties": {
      "title": {
        "type": "string",
        "description": "Table title"
      },
      "columns": {
        "type": "array",
        "items": { "type": "string" },
        "description": "Column headers"
      },
      "rows": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "dimension": { "type": "string" },
            "previous_value": { "type": "string" },
            "current_value": { "type": "string" },
            "delta": { "type": "string" },
            "is_top_contributor": { "type": "boolean" }
          }
        },
        "description": "Table rows with comparison data"
      }
    },
    "required": ["title", "columns", "rows"]
  }
}
```

---

## 9. Frontend Specification (Lovable)

### Layout
```
+--------------------------------------------------+
|           Voice-to-Data Analytics Agent           |
|                                                   |
|  +---------------------+  +--------------------+ |
|  |   Conversation      |  |  Comparison Table  | |
|  |                     |  |                    | |
|  |  You: "Why did      |  |  Engagement Drop   | |
|  |  engagement drop?"  |  |  Analysis          | |
|  |                     |  |                    | |
|  |  Agent: "Which      |  |  Dimension | Prev  | |
|  |  platform?"         |  |  --------- | ----  | |
|  |                     |  |  Mobile    | 45.2  | |
|  |  You: "All of them" |  |  Web       | 32.1  | |
|  |                     |  |  Tablet    | 12.4  | |
|  |                     |  |                    | |
|  +---------------------+  +--------------------+ |
|                                                   |
|              [ 🎤 Tap to Speak ]                  |
|                                                   |
+--------------------------------------------------+
```

### Components
1. **Header:** App title + minimal branding
2. **Conversation Panel (Left):** Scrolling transcript of the voice conversation
3. **Visualization Panel (Right):** Comparison table that updates when results arrive
4. **Mic Button (Bottom Center):** Large, prominent — single tap to start/stop listening
5. **Status Indicator:** Shows current state (Listening... / Thinking... / Speaking...)

### Styling
- Dark theme (executive feel)
- Minimal, clean design
- Highlighted rows in comparison table (green/red for positive/negative deltas)
- Smooth transitions when table data loads

---

## 10. Hathora Integration

### Session Management
- On page load → create a Hathora room (session)
- Room stores:
  ```json
  {
    "sessionId": "uuid",
    "conversationHistory": [],
    "currentContext": {
      "timePeriod": null,
      "platform": null,
      "segment": null
    },
    "lastQueryResults": null,
    "displayState": {
      "tableData": null,
      "status": "idle"
    }
  }
  ```
- VAPI function calls update the Hathora room state
- Lovable frontend subscribes to Hathora room state changes → re-renders UI

### Why Hathora (not just local state)
- Decouples voice processing (VAPI backend) from frontend rendering (Lovable)
- Enables the "live update" demo moment — table appears as agent speaks
- Foundation for post-MVP multi-exec collaboration

---

## 11. MVP Scope Cuts (If Running Behind)

**Priority order — cut from bottom up if behind schedule:**

| Priority | Feature | Cut Strategy | Impact |
|----------|---------|-------------|--------|
| P0 (Must have) | Voice input → text answer | Cannot cut — this IS the product | Fatal |
| P0 (Must have) | SQL generation + query | Cannot cut — core value prop | Fatal |
| P1 (Should have) | Voice output (TTS) | Keep voice in, return text-only answers | Reduces wow factor but works |
| P1 (Should have) | Comparison table | Show text-only ranked list instead of table | Still functional, less visual |
| P2 (Nice to have) | Smart clarifications | Drop to single-turn Q&A (no clarifying questions) | Simpler but less impressive |
| P2 (Nice to have) | Hathora session state | Use local state in the frontend instead | Loses real-time sync, still works |

---

## 12. Post-MVP Roadmap

### Phase 2: Multi-Turn Memory (Top Priority — User Selected)
- Agent remembers full conversation context across turns
- "Now compare that to Q3" works without restating the metric
- Requires Hathora session state (MVP foundation)
- LLM receives conversation history with each turn

### Phase 3: Real Data Connectors
- Connect to Snowflake, BigQuery, or Redshift
- Schema auto-discovery (LLM reads metadata)
- Credential management + row-level security

### Phase 4: Proactive Anomaly Detection
- Agent surfaces anomalies before being asked
- "Good morning. I noticed churn spiked 15% in the enterprise segment yesterday."
- Scheduled daily analysis + push notifications

### Phase 5: Multi-Executive Collaboration
- Multiple execs in the same Hathora room
- One person asks a question → everyone sees the answer
- Leverages Hathora's multiplayer infrastructure

### Phase 6: Role-Based Context
- User selects role (CPO, CEO, VP Engineering)
- Agent pre-loads relevant metrics and adjusts vocabulary
- Permission-based data access

---

## 13. Success Criteria (Hackathon Demo)

| Criteria | Measurement |
|----------|-------------|
| Voice question is understood correctly | Agent's response addresses the actual question asked |
| SQL generates valid results | No SQL errors, results match the expected data |
| Answer is executive-friendly | No jargon, concise, ranked by impact |
| Comparison table renders | Table appears on screen with correct before/after data |
| End-to-end latency | < 10 seconds from question to answer (acceptable for demo) |
| Demo narrative works | The "2% engagement drop" story flows naturally start to finish |

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| VAPI function calling is unreliable | Medium | High | Pre-test function calling before building frontend. Fallback: hardcode demo responses |
| SQL generation errors | High | High | Narrow schema + few-shot examples in system prompt. Fallback: pre-written SQL templates |
| Lovable + Hathora integration takes too long | Medium | Medium | Cut Hathora, use Lovable local state |
| Dataset doesn't tell the right story | Low | High | Using synthetic data — we control the narrative |
| Voice recognition fails in noisy environment | Medium | Low | Have a text input fallback on the UI |
| 2-hour time budget exceeded | High | Medium | Follow priority cut table (Section 11) |

---

## 15. 2-Hour Build Plan (Suggested)

| Time | Task | Output |
|------|------|--------|
| 0:00 - 0:20 | Generate synthetic dataset + load into SQLite | `engagement.db` with 3 tables |
| 0:20 - 0:50 | Configure VAPI assistant (system prompt, functions, voice) | Working voice agent with function calling |
| 0:50 - 1:10 | Build backend: function call handler (SQL execution + results) | API endpoint that VAPI calls |
| 1:10 - 1:35 | Build Lovable frontend (chat panel + comparison table + mic button) | Working UI |
| 1:35 - 1:50 | Integrate Hathora for session state + connect frontend to backend | End-to-end flow |
| 1:50 - 2:00 | Test full demo flow + fix bugs | Demo-ready |

---

## Appendix A: Sample System Prompt for VAPI

```
You are an executive analytics assistant specializing in product engagement data.

You have access to a product engagement database with the following tables:

1. daily_metrics (date, platform, segment, dau, wau, mau, session_duration_avg, sessions_per_user)
2. feature_usage (date, feature_name, platform, segment, adoption_rate, sessions_with_feature, drop_off_rate)
3. funnel_metrics (date, funnel_step, platform, segment, conversion_rate, users_count)

Platforms: web, mobile, tablet
Segments: free, pro, enterprise
Time range: Last 8 weeks

BEHAVIOR:
- If the user's question is specific, generate a SQL query immediately using the query_analytics function.
- If the user's question is vague or could benefit from narrowing, ask ONE clarifying question before querying.
- Never show SQL to the user. Speak in executive-friendly language.
- When presenting results, lead with the top finding, then list 2-3 contributing factors ranked by impact.
- Always call display_comparison_table to show a visual comparison on the user's screen.
- If asked about data you don't have, say: "I don't have data for that. I can help with product engagement metrics like daily active users, session duration, feature adoption, and conversion funnels."

EXAMPLE:
User: "Why did engagement drop last week?"
You: "Are you asking about all platforms or a specific one like mobile or web?"
User: "All platforms."
[Call query_analytics to get week-over-week comparison across all dimensions]
[Call display_comparison_table with the results]
You: "The overall engagement dip of about 2% was mainly driven by three things. Mobile session duration dropped 8 percent, likely tied to Tuesday's app update. Onboarding completion in the free tier fell 12 percent. And Feature X adoption declined 5 percent week over week. I've put the full breakdown on your screen."
```

---

## Appendix B: Sample Synthetic Data Spec

```python
# Key data points to engineer into the synthetic dataset:

# Week N-1 (previous week - "normal"):
# - Overall DAU: ~50,000
# - Mobile session duration: ~6.2 min
# - Free tier onboarding: ~68% completion
# - Feature X adoption: ~34%

# Week N (current week - "the drop"):
# - Overall DAU: ~49,000 (-2%)
# - Mobile session duration: ~5.7 min (-8%)
# - Free tier onboarding: ~60% completion (-12%)
# - Feature X adoption: ~32.3% (-5%)

# All other metrics stay relatively flat to make the signal clear.
```

# Lovable Prompt

Paste this into Lovable (lovable.dev) to generate the base app. Then add the VAPI integration code from `frontend/src/hooks/`.

---

Build a real-time voice analytics agent dashboard with the following specs:

**Layout:** Full-screen dark theme app with three sections:
1. **Header** (top bar): App title "Voice-to-Data" with subtitle "Executive Analytics Agent" on the left. A status indicator on the right showing states: "Ready" (gray dot), "Listening..." (green pulsing dot), "Analyzing..." (blue pulsing dot), "Speaking..." (purple pulsing dot).
2. **Main area** split 50/50 horizontally:
   - **Left panel ("Conversation"):** A scrolling chat transcript. User messages appear right-aligned with green-tinted bubbles. Agent messages appear left-aligned with dark gray bubbles. Each message has a tiny label: "You" or "Analyst". Show a placeholder icon + "Tap the mic to start a conversation" when empty.
   - **Right panel ("Analysis"):** A comparison table that shows data after analysis. Columns: Dimension, Previous, Current, Change. Negative deltas in red, positive in green. Rows marked as "top contributor" get a subtle red background tint and a small red dot next to the dimension name. Show a placeholder icon + "Data will appear here after analysis" when empty.
3. **Footer:** A large centered circular mic button. Green when idle ("Tap to speak"), red with a pulsing ring animation when active ("Tap to end"), yellow spinner when connecting.

**Tech:**
- React + TypeScript + Tailwind CSS
- Dark theme (gray-950 background, gray-100 text)
- Install the `@vapi-ai/web` npm package for voice integration
- Read VITE_VAPI_PUBLIC_KEY and VITE_VAPI_ASSISTANT_ID from environment variables
- SSE connection to a backend at VITE_BACKEND_URL for receiving comparison table data

**Styling:** Clean, minimal, executive feel. Inter font. Thin borders (gray-800/50). Smooth scroll on conversation panel. Custom thin scrollbar. No unnecessary decoration.

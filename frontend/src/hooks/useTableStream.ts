import { useEffect, useRef, useState } from "react";

export interface TableRow {
  dimension: string;
  previous_value: string;
  current_value: string;
  delta: string;
  is_top_contributor: boolean;
}

export interface TableData {
  title: string | null;
  columns: string[];
  rows: TableRow[];
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export function useTableStream(callId: string | null, credential: string | null): TableData {
  const [table, setTable] = useState<TableData>({
    title: null,
    columns: [],
    rows: [],
  });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!callId || !credential) return;

    const abort = new AbortController();
    abortRef.current = abort;

    streamWithFetch(callId, credential, setTable, abort.signal).then(
      () => {
        // Stream ended cleanly (server closed connection), fall back to polling
        if (!abort.signal.aborted) {
          pollTable(callId, credential, setTable, abort.signal);
        }
      },
      () => {
        // Stream errored, fall back to polling
        if (!abort.signal.aborted) {
          pollTable(callId, credential, setTable, abort.signal);
        }
      }
    );

    return () => {
      abort.abort();
      abortRef.current = null;
    };
  }, [callId, credential]);

  return table;
}

/** SSE via fetch + ReadableStream — allows Authorization header (no token in URL). */
async function streamWithFetch(
  callId: string,
  credential: string,
  setTable: (t: TableData) => void,
  signal: AbortSignal
) {
  const res = await fetch(`${BACKEND_URL}/api/table-stream/${callId}`, {
    headers: { Authorization: `Bearer ${credential}` },
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`SSE failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (!signal.aborted) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(line.slice(6));
        if (data.title) {
          setTable({
            title: data.title,
            columns: data.columns || [],
            rows: data.rows || [],
          });
        }
      } catch {
        // Ignore parse errors from heartbeats
      }
    }
  }
}

/** Fallback polling if SSE fails */
async function pollTable(
  callId: string,
  credential: string,
  setTable: (t: TableData) => void,
  signal: AbortSignal
) {
  while (!signal.aborted) {
    try {
      const res = await fetch(`${BACKEND_URL}/api/table/${callId}`, {
        headers: { Authorization: `Bearer ${credential}` },
        signal,
      });
      if (res.status === 401) break; // Token expired, stop polling
      const data = await res.json();
      if (data.title) {
        setTable({
          title: data.title,
          columns: data.columns || [],
          rows: data.rows || [],
        });
      }
    } catch {
      if (signal.aborted) break;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
}

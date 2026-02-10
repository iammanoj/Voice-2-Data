import { useEffect, useState } from "react";

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

export function useTableStream(callId: string | null): TableData {
  const [table, setTable] = useState<TableData>({
    title: null,
    columns: [],
    rows: [],
  });

  useEffect(() => {
    if (!callId) return;

    const eventSource = new EventSource(
      `${BACKEND_URL}/api/table-stream/${callId}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
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
    };

    eventSource.onerror = () => {
      // SSE will auto-reconnect; fall back to polling if needed
      eventSource.close();
      pollTable(callId, setTable);
    };

    return () => eventSource.close();
  }, [callId]);

  return table;
}

/** Fallback polling if SSE fails */
function pollTable(
  callId: string,
  setTable: (t: TableData) => void
) {
  const BACKEND_URL =
    import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
  let active = true;

  const poll = async () => {
    while (active) {
      try {
        const res = await fetch(`${BACKEND_URL}/api/table/${callId}`);
        const data = await res.json();
        if (data.title) {
          setTable({
            title: data.title,
            columns: data.columns || [],
            rows: data.rows || [],
          });
        }
      } catch {
        // ignore
      }
      await new Promise((r) => setTimeout(r, 2000));
    }
  };
  poll();

  return () => {
    active = false;
  };
}

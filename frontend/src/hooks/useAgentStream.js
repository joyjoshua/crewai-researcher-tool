import { useState, useEffect, useRef } from "react";
import { supabase } from "../lib/supabase";

/**
 * SSE stream from FastAPI. Retries with exponential backoff if the connection drops.
 */
export function useAgentStream(jobId) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const sourceRef = useRef(null);
  const retriesRef = useRef(0);
  const maxRetries = 3;

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;
    retriesRef.current = 0;
    queueMicrotask(() => {
      setStatus("running");
      setEvents([]);
    });

    async function connect() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (cancelled) return;

      const token = session?.access_token;
      if (!token) {
        setStatus("error");
        return;
      }

      const url = `/api/report/stream/${jobId}?token=${encodeURIComponent(token)}`;
      const source = new EventSource(url);
      sourceRef.current = source;

      source.onmessage = (e) => {
        try {
          const event = JSON.parse(e.data);
          setEvents((prev) => [...prev, event]);
          retriesRef.current = 0;

          if (event.type === "flow_complete") {
            setStatus("done");
            source.close();
          } else if (event.type === "error") {
            setStatus("error");
            source.close();
          }
        } catch (err) {
          console.error("Failed to parse SSE event:", err);
        }
      };

      source.onerror = () => {
        source.close();
        if (cancelled) return;
        if (retriesRef.current < maxRetries) {
          retriesRef.current += 1;
          const delay = Math.min(1000 * 2 ** retriesRef.current, 10000);
          console.log(`SSE reconnecting in ${delay}ms (attempt ${retriesRef.current})`);
          setTimeout(() => {
            if (!cancelled) void connect();
          }, delay);
        } else {
          setStatus("error");
        }
      };
    }

    void connect();

    return () => {
      cancelled = true;
      sourceRef.current?.close();
    };
  }, [jobId]);

  return { events, status };
}

export function connectStopSSE(onMsg) {
  const base = import.meta.env.VITE_API_BASE || "http://localhost:8000";
  const es = new EventSource(`${base}/realtime/stop-events`);
  es.onmessage = (ev) => {
    try { onMsg(JSON.parse(ev.data)); } catch { onMsg({ raw: ev.data }); }
  };
  return () => es.close();
}

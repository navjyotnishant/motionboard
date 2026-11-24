// Server-sent events fed from change_event. The engine, chat and Studio all write there, so every client
// sees every change within about half a second.
import { connection } from "next/server";
import { raw } from "@/lib/db";

export async function GET(req: Request) {
  await connection();
  const url = new URL(req.url);
  let since = Number(url.searchParams.get("since") || req.headers.get("last-event-id") || 0);
  if (!since) since = (raw().prepare("SELECT COALESCE(MAX(seq), 0) AS s FROM change_event").get() as { s: number }).s;
  const enc = new TextEncoder();
  const stmt = raw().prepare(
    "SELECT seq, entity, entity_id, kind, actor FROM change_event WHERE seq > ? ORDER BY seq LIMIT 500",
  );
  let timer: ReturnType<typeof setInterval> | undefined;
  const stream = new ReadableStream({
    start(ctrl) {
      ctrl.enqueue(enc.encode(`retry: 1000\n: connected ${since}\n\n`));
      let beat = 0;
      timer = setInterval(() => {
        try {
          const rows = stmt.all(since) as { seq: number }[];
          for (const r of rows) {
            ctrl.enqueue(enc.encode(`id: ${r.seq}\ndata: ${JSON.stringify(r)}\n\n`));
            since = r.seq;
          }
          if (++beat % 30 === 0) ctrl.enqueue(enc.encode(": ping\n\n"));
        } catch {
          clearInterval(timer);
          try { ctrl.close(); } catch { /* already closed */ }
        }
      }, 500);
      req.signal.addEventListener("abort", () => {
        clearInterval(timer);
        try { ctrl.close(); } catch { /* already closed */ }
      });
    },
    cancel() {
      clearInterval(timer);
    },
  });
  return new Response(stream, {
    headers: { "content-type": "text/event-stream", "cache-control": "no-store", connection: "keep-alive" },
  });
}

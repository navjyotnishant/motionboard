import fs from "node:fs";
import { Readable } from "node:stream";
import { connection, NextResponse } from "next/server";
import { contentType, parseRange, resolveMedia } from "@/lib/media";

export async function GET(req: Request) {
  await connection();
  const p = new URL(req.url).searchParams.get("path") || "";
  const file = resolveMedia(p);
  if (!file) return NextResponse.json({ error: "FORBIDDEN" }, { status: 403 });
  const size = fs.statSync(file).size;
  const type = contentType(file);
  const range = parseRange(req.headers.get("range"), size);
  const base = { "content-type": type, "accept-ranges": "bytes", "cache-control": "no-cache" };
  if (req.headers.get("range") && !range) {
    return new Response(null, { status: 416, headers: { "content-range": `bytes */${size}` } });
  }
  if (range) {
    const body = Readable.toWeb(fs.createReadStream(file, range)) as ReadableStream;
    return new Response(body, {
      status: 206,
      headers: { ...base, "content-range": `bytes ${range.start}-${range.end}/${size}`,
        "content-length": String(range.end - range.start + 1) },
    });
  }
  const body = Readable.toWeb(fs.createReadStream(file)) as ReadableStream;
  return new Response(body, { headers: { ...base, "content-length": String(size) } });
}

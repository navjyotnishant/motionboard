import { connection, NextResponse } from "next/server";
import { build, MbBridgeError, runMb } from "@/lib/mb";

export async function POST(req: Request) {
  await connection();
  let body: { action?: string; args?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad JSON" }, { status: 400 });
  }
  try {
    const args = build(body.action || "", body.args);
    const report = await runMb(args);
    return NextResponse.json(report);
  } catch (e) {
    if (e instanceof MbBridgeError) return NextResponse.json({ error: e.message }, { status: e.status });
    throw e;
  }
}

import { connection, NextResponse } from "next/server";
import { build, runMb } from "@/lib/mb";

export async function GET() {
  await connection();
  const r = await runMb(build("modes", {}), 30_000);
  return NextResponse.json(r.ok ? r.data : { modes: [], looks: [], error: r.error });
}

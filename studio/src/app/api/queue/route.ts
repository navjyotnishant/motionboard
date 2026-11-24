import { connection, NextResponse } from "next/server";
import { queue } from "@/lib/data";
import { sampleNow } from "@/lib/memory";

export async function GET() {
  await connection();
  return NextResponse.json({ ...queue(), now: await sampleNow() });
}

import { connection, NextResponse } from "next/server";
import { queue } from "@/lib/data";
import { sampleSystem } from "@/lib/memory";

export async function GET() {
  await connection();
  return NextResponse.json({ ...queue(), now: await sampleSystem() });
}

// Start a project from the Studio: save an uploaded song (if any) under the projects folder, write the lyrics
// to a file, then `mb project new` and `mb analyze`. Returns the project id and the analysis report.
import fs from "node:fs";
import path from "node:path";
import { connection, NextResponse } from "next/server";
import { PROJECTS_ROOT } from "@/lib/config";
import { build, MbBridgeError, runMb } from "@/lib/mb";

const AUDIO = new Set([".wav", ".mp3", ".m4a", ".aac", ".flac", ".aiff", ".aif", ".ogg"]);

export async function POST(req: Request) {
  await connection();
  const form = await req.formData();
  const title = String(form.get("title") || "").trim();
  const lyrics = String(form.get("lyrics") || "");
  const idea = String(form.get("idea") || "");
  const aspect = String(form.get("aspect") || "9:16");
  const look = String(form.get("look") || "stylized");
  let song = String(form.get("song_path") || "").trim();
  const upload = form.get("song_file");
  const staging = path.join(PROJECTS_ROOT, "_uploads", `${Date.now()}`);
  try {
    if (upload && typeof upload !== "string" && upload.size > 0) {
      const ext = path.extname(upload.name).toLowerCase();
      if (!AUDIO.has(ext)) return NextResponse.json({ error: `not an audio file (${ext})` }, { status: 400 });
      fs.mkdirSync(staging, { recursive: true });
      song = path.join(staging, `song${ext}`);
      fs.writeFileSync(song, Buffer.from(await upload.arrayBuffer()));
    }
    if (!song) return NextResponse.json({ error: "pick a song file or give its path" }, { status: 400 });
    if (!path.isAbsolute(song) || !fs.existsSync(/*turbopackIgnore: true*/ song)) {
      return NextResponse.json({ error: `song not found: ${song}` }, { status: 400 });
    }
    let lyricsFile: string | undefined;
    if (lyrics.trim()) {
      fs.mkdirSync(staging, { recursive: true });
      lyricsFile = path.join(staging, "lyrics.txt");
      fs.writeFileSync(lyricsFile, lyrics);
    }
    const created = await runMb(build("project_new", { title, song, lyrics_file: lyricsFile, idea: idea || undefined, aspect, look }));
    if (!created.ok) return NextResponse.json({ created }, { status: 422 });
    const pid = created.project as string;
    const analyzed = await runMb(build("analyze", { project: pid }));
    return NextResponse.json({ project: pid, created, analyzed });
  } catch (e) {
    if (e instanceof MbBridgeError) return NextResponse.json({ error: e.message }, { status: e.status });
    throw e;
  } finally {
    // The engine copies the song and lyrics into the project folder; the staging copy is not needed.
    fs.rmSync(staging, { recursive: true, force: true });
  }
}

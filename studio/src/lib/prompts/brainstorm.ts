// Prompt for `claude -p` when the creator brainstorms from the Studio. The answer must be JSON only.
export function brainstormPrompt(input: {
  title: string; lyrics: string; idea: string; aspect: string; tempo: number | null; shots: number;
  modes: { slug: string; name: string; summary: string }[]; looks: string[];
  answers: { mood?: string; world?: string; characters?: string; look?: string };
}): string {
  return `You are helping a creator plan a short vertical music video storyboard.

Song: ${input.title}
Tempo: ${input.tempo ? Math.round(input.tempo) + " BPM" : "unknown"}
Number of shots: ${input.shots}
Aspect: ${input.aspect}
Creator's idea: ${input.idea || "(none)"}
Mood they want: ${input.answers.mood || "(open)"}
World or setting: ${input.answers.world || "(open)"}
Characters: ${input.answers.characters || "(open)"}
Preferred look: ${input.answers.look || "(open)"}

Lyrics of the segment:
${input.lyrics.slice(0, 2000)}

Story modes (pick one per concept, by slug):
${input.modes.map((m) => `- ${m.slug}: ${m.summary}`).join("\n")}

Looks (pick one per concept): ${input.looks.join(", ")}

Write three clearly different concepts. Rules:
- Do not invent lyrics. Do not name real people, brands or places.
- Characters in capitals as one word (HER, HIM, SINGER), so the engine can link them to shots.
- No follow or subscribe asks. No text in the images.
- Each concept has exactly ${input.shots} shot ideas in order, one per shot.

Answer with JSON only, no prose, in this shape:
{"concepts":[{"title":"...","premise":"two sentences","hero_image_idea":"one sentence","mode":"slug","look":"slug",
"sample_shots":["three short shot lines for the card"],
"shots":[{"visual":"...","action":"...","camera":"...","has_figure":true,"lip_sync":false}]}]}`;
}

export function extractJson(text: string): unknown {
  const start = text.indexOf("{");
  const end = text.lastIndexOf("}");
  if (start < 0 || end <= start) throw new Error("no JSON in the answer");
  return JSON.parse(text.slice(start, end + 1));
}

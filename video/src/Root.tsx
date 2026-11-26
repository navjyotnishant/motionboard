import React from "react";
import { AbsoluteFill, Composition, Sequence, Still } from "remotion";
import { Cover } from "./Cover";
import { C, Progress } from "./kit";
import { Hook, Images, Listen, Motion, Storyboard } from "./scenes1";
import { End, Finish, Studio, Takes } from "./scenes2";
import { Free } from "./scenes3";

// Every length is a whole number of beats at 120 BPM (15 frames), so cuts land on the music bed.
export const SCENES: [React.FC<{ len: number }>, number][] = [
  [Hook, 150], [Listen, 180], [Storyboard, 210], [Images, 180], [Motion, 210], [Takes, 180], [Free, 180], [Studio, 210], [Finish, 240], [End, 180],
];
export const TOTAL = SCENES.reduce((a, [, n]) => a + n, 0);

const Overview: React.FC = () => {
  let at = 0;
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      {SCENES.map(([S, len], i) => {
        const from = at; at += len;
        return <Sequence key={i} from={from} durationInFrames={len}><S len={len} /></Sequence>;
      })}
      <Progress total={TOTAL} />
    </AbsoluteFill>
  );
};

export const Root: React.FC = () => (
  <>
    <Composition id="Overview" component={Overview} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
    <Still id="Cover" component={Cover} width={1920} height={1080} />
  </>
);

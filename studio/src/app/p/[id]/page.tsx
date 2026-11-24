"use client";
import { Suspense } from "react";
import { useParams } from "next/navigation";
import { BoardView } from "@/components/board/BoardView";

function Inner() {
  const { id } = useParams<{ id: string }>();
  return <BoardView id={id} />;
}

export default function ProjectPage() {
  return (
    <Suspense fallback={<div className="p-6 text-fg3">Loading…</div>}>
      <Inner />
    </Suspense>
  );
}

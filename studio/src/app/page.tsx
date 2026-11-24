import { TopBar } from "@/components/ui/TopBar";
import { ProjectBin } from "@/components/bin/ProjectBin";

export default function Home() {
  return (
    <div className="flex h-full flex-col">
      <TopBar title="Projects" />
      <main className="scroll-thin flex-1 overflow-auto p-6">
        <ProjectBin />
      </main>
    </div>
  );
}

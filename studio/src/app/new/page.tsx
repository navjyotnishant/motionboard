import { TopBar } from "@/components/ui/TopBar";
import { StartFlow } from "@/components/start/StartFlow";

export default function NewProject() {
  return (
    <div className="flex h-full flex-col">
      <TopBar title="New project" />
      <main className="scroll-thin flex-1 overflow-auto p-6">
        <StartFlow />
      </main>
    </div>
  );
}

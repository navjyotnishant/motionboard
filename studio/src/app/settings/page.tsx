import { TopBar } from "@/components/ui/TopBar";
import { Settings } from "@/components/settings/Settings";

export default function SettingsPage() {
  return (
    <div className="flex h-full flex-col">
      <TopBar title="Settings" />
      <main className="scroll-thin flex-1 overflow-auto p-6"><Settings /></main>
    </div>
  );
}

import Link from "next/link";

export function TopBar({ title, children }: { title?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-4 border-b border-line bg-s1 px-4">
      <Link href="/" className="flex items-center gap-2 text-fg hover:text-accent">
        <span className="inline-block h-3 w-3 rounded-sm bg-accent" />
        <span className="text-[13px] font-semibold tracking-wide">MOTIONBOARD</span>
      </Link>
      {title && <div className="min-w-0 truncate text-[13px] text-fg2">{title}</div>}
      <div className="ml-auto flex items-center gap-2">{children}</div>
    </header>
  );
}

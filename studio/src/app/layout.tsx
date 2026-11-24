import type { Metadata } from "next";
import "./globals.css";
import { ToastProvider } from "@/components/ui/Toast";
import { Appearance } from "@/components/ui/Appearance";

export const metadata: Metadata = {
  title: "Motionboard Studio",
  description: "Storyboard first music videos, on your own machine",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Appearance />
        <ToastProvider>{children}</ToastProvider>
      </body>
    </html>
  );
}

"use client";
import { useEffect } from "react";
import { applyAppearance } from "@/components/settings/Settings";

/** Applies the saved theme and accent on every page. */
export function Appearance() {
  useEffect(() => { applyAppearance(); }, []);
  return null;
}

import type { Metadata } from "next";
import { ResearchSettingsView } from "@/components/research/settings-view";

export const metadata: Metadata = { title: "Research settings" };

export default function ResearchSettingsPage() {
  return <ResearchSettingsView />;
}

import type { Metadata } from "next";
import { HistoryView } from "@/components/research/history-view";

export const metadata: Metadata = { title: "Research history" };

export default function ResearchHistoryPage() {
  return <HistoryView />;
}

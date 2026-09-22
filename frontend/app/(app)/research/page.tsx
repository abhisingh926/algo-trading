import type { Metadata } from "next";
import { ResearchOverview } from "@/components/research/research-overview";

export const metadata: Metadata = { title: "Research" };

export default function ResearchPage() {
  return <ResearchOverview />;
}

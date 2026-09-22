import type { Metadata } from "next";
import { SectorsView } from "@/components/research/sectors-view";

export const metadata: Metadata = { title: "Sector rotation" };

export default function ResearchSectorsPage() {
  return <SectorsView />;
}

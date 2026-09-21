import type { Metadata } from "next";
import { StrategyBuilder } from "@/components/trading/strategy-builder";

export const metadata: Metadata = { title: "Create Strategy" };

export default function NewStrategyPage() {
  return <StrategyBuilder />;
}

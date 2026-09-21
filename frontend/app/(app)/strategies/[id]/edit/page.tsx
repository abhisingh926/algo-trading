import type { Metadata } from "next";
import { StrategyBuilder } from "@/components/trading/strategy-builder";

export const metadata: Metadata = { title: "Edit Strategy" };

export default async function EditStrategyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <StrategyBuilder strategyId={id} />;
}

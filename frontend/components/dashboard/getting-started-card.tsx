"use client";

import Link from "next/link";
import { ArrowRight, X } from "lucide-react";
import { findNextStep } from "@/components/guide/onboarding-checklist";
import { ProgressBar } from "@/components/layout/progress-bar";
import { buttonVariants, Button } from "@/components/ui/button";
import { useOnboarding } from "@/hooks/use-guide";
import { useLocalFlag } from "@/lib/local-flag";

const DISMISS_KEY = "algo.guide.card_dismissed";

/** Slim dashboard nudge. Hidden while loading, on error, when everything is done, or once dismissed. */
export function GettingStartedCard() {
  const { data } = useOnboarding();
  const [dismissed, setDismissed] = useLocalFlag(DISMISS_KEY);

  if (!data || data.all_done || dismissed) return null;
  const next = findNextStep(data);

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border bg-card px-4 py-3">
      <div className="min-w-48 flex-1">
        <p className="text-sm font-medium">
          Getting started: <span className="tabular">{data.completed}</span> of{" "}
          <span className="tabular">{data.total}</span> done
        </p>
        <ProgressBar value={data.percent} label="Getting started progress" className="mt-1.5" />
        {next ? (
          <p className="mt-1.5 truncate text-xs text-muted-foreground">
            Next: <span className="font-medium text-foreground">{next.title}</span>
          </p>
        ) : null}
      </div>
      <Link href="/guide" className={buttonVariants({ size: "sm" })}>
        Open guide <ArrowRight />
      </Link>
      <Button variant="ghost" size="icon-sm" aria-label="Dismiss getting started card" onClick={() => setDismissed(true)}>
        <X />
      </Button>
    </div>
  );
}

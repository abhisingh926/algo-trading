"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle2, Circle, PartyPopper } from "lucide-react";
import { ProgressBar } from "@/components/layout/progress-bar";
import { ErrorState } from "@/components/tables/states";
import { Pill } from "@/components/trading/badges";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useOnboarding } from "@/hooks/use-guide";
import { cn } from "@/lib/utils";
import type { Onboarding, OnboardingStep } from "@/types";

/** `next_step` is documented as a string; match it against the step key or (defensively) the title. */
export function findNextStep(onboarding: Onboarding): OnboardingStep | null {
  if (onboarding.all_done) return null;
  const byName = onboarding.steps.find(
    (s) => !s.done && (s.key === onboarding.next_step || s.title === onboarding.next_step),
  );
  return byName ?? onboarding.steps.find((s) => !s.done && !s.optional) ?? null;
}

const isInternalRoute = (href: string) => href.startsWith("/") && !href.startsWith("//");

export function OnboardingChecklist() {
  const { data, isLoading, error, refetch } = useOnboarding();

  if (isLoading) {
    return (
      <div className="grid gap-3 rounded-lg border bg-card p-4">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-1.5 w-full" />
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }
  if (error && !data) {
    return (
      <div className="rounded-lg border bg-card">
        <ErrorState error={error} onRetry={() => void refetch()} />
      </div>
    );
  }
  if (!data) return null;

  const next = findNextStep(data);

  return (
    <div className="rounded-lg border bg-card">
      <div className="border-b p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold">Getting started</h2>
          <p className="tabular text-sm text-muted-foreground">
            {data.completed} of {data.total} done · {Math.round(data.percent)}%
          </p>
        </div>
        <ProgressBar value={data.percent} label="Getting started progress" className="mt-2" />
        {data.all_done ? (
          <p className="mt-2 flex items-center gap-1.5 text-sm text-profit">
            <PartyPopper className="size-4" aria-hidden /> All steps are done. Keep paper trading and reviewing your
            trades before you even think about real money.
          </p>
        ) : null}
      </div>
      <ol className="divide-y">
        {data.steps.map((step, i) => {
          const isNext = next?.key === step.key;
          return (
            <li
              key={step.key}
              aria-current={isNext ? "step" : undefined}
              className={cn(
                "flex flex-wrap items-start gap-x-3 gap-y-2 p-4 sm:flex-nowrap",
                isNext && "bg-info/5 shadow-[inset_3px_0_0_var(--info)]",
              )}
            >
              {step.done ? (
                <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-profit" aria-label="Done" />
              ) : (
                <Circle className="mt-0.5 size-5 shrink-0 text-muted-foreground/60" aria-label="Not done yet" />
              )}
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-2 text-sm font-medium">
                  <span className={cn(step.done && "text-muted-foreground line-through decoration-1")}>
                    {i + 1}. {step.title}
                  </span>
                  {step.optional ? <Pill>Optional</Pill> : null}
                  {isNext ? <Pill tone="info">Next step</Pill> : null}
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">{step.description}</p>
              </div>
              {isInternalRoute(step.href) ? (
                <Link
                  href={step.href}
                  className={buttonVariants({
                    variant: isNext ? "default" : step.done ? "ghost" : "outline",
                    size: "sm",
                  })}
                >
                  {step.done ? "Open" : isNext ? "Do this now" : "Open"}
                  {!step.done ? <ArrowRight /> : null}
                </Link>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

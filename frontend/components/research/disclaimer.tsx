import { Info } from "lucide-react";
import { SHORT_DISCLAIMER } from "@/lib/research";
import { cn } from "@/lib/utils";

/** Shown on every research page. */
export function ResearchDisclaimer({ className, text = SHORT_DISCLAIMER }: { className?: string; text?: string }) {
  return (
    <p
      role="note"
      className={cn("flex gap-2 rounded-lg border bg-muted/40 px-3 py-2 text-xs text-muted-foreground", className)}
    >
      <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      <span>{text}</span>
    </p>
  );
}

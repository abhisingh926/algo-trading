import { cn } from "@/lib/utils";
import type { ResearchReport } from "@/types/research";

function ListCard({
  title,
  description,
  items,
  empty,
  className,
}: {
  title: string;
  description?: string;
  items: string[];
  empty: string;
  className?: string;
}) {
  return (
    <section className={cn("rounded-lg border bg-card p-4", className)} aria-label={title}>
      <h3 className="text-sm font-semibold">{title}</h3>
      {description ? <p className="text-xs text-muted-foreground">{description}</p> : null}
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="mt-2 grid list-disc gap-1.5 pl-4 text-sm marker:text-muted-foreground">
          {items.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** The four plain-language lists of a report, shown exactly as the backend wrote them. */
export function InsightLists({ report }: { report: ResearchReport }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <ListCard
        title="Why it appears on the list"
        description="The strongest reasons behind the score."
        items={report.why_listed}
        empty="No reasons were recorded."
      />
      <ListCard title="Risks" items={report.risks} empty="No risks were recorded. That does not mean there are none." />
      <ListCard
        title="What would invalidate the setup"
        description="If these happen, the reasoning above no longer holds."
        items={report.invalidation}
        empty="No invalidation levels were recorded."
      />
      <ListCard
        title="Not assessed"
        description="Things this report did not look at."
        items={report.not_assessed}
        empty="Everything in scope was assessed."
      />
    </div>
  );
}

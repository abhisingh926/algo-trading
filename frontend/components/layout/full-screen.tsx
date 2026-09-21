"use client";

import { Loader2, ServerCrash } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/api";
import { errorText } from "@/lib/toast";

export function FullScreenLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" /> {label}
    </div>
  );
}

export function BackendUnreachable({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { title, description } = errorText(error);
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-2 px-4 text-center">
      <ServerCrash className="size-8 text-loss" aria-hidden />
      <h1 className="text-base font-semibold">{title}</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        {description ?? "The trading backend did not respond."}
      </p>
      <p className="text-xs text-muted-foreground">
        API: <code className="font-mono">{API_BASE_URL}</code>
      </p>
      <Button className="mt-2" variant="outline" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

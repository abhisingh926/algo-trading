"use client";

import { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toastError, toastSuccess } from "@/lib/toast";
import { researchService } from "@/services/research";

/** Fetches the export with the bearer token as a blob, then saves it: a plain link could not send the token. */
export function ExportButtons({ symbol, runId }: { symbol: string; runId: string }) {
  const [busy, setBusy] = useState<"json" | "csv" | null>(null);

  async function download(format: "json" | "csv") {
    setBusy(format);
    try {
      const { blob, filename } = await researchService.exportReport(symbol, format, runId);
      const name = filename ?? `${symbol}-research.${format}`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toastSuccess("Export downloaded", name);
    } catch (err) {
      toastError(err);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex items-center gap-2">
      {(["json", "csv"] as const).map((f) => (
        <Button key={f} variant="outline" size="sm" disabled={busy !== null} onClick={() => void download(f)}>
          {busy === f ? <Loader2 className="animate-spin" /> : <Download />} {f.toUpperCase()}
        </Button>
      ))}
    </div>
  );
}

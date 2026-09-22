"use client";

import { useId, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { reportHref } from "@/lib/research";

/** "Research a symbol": opens /research/[symbol]. Accepts symbols such as M&M and BAJAJ-AUTO. */
export function SymbolSearch({ suggestions = [] }: { suggestions?: string[] }) {
  const router = useRouter();
  const [value, setValue] = useState("");
  const listId = useId();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const symbol = value.trim().toUpperCase();
    if (!symbol) return;
    router.push(reportHref(symbol));
  };

  return (
    <form onSubmit={submit} role="search" className="flex items-center gap-2">
      <div className="relative">
        <Search
          className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <Input
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          list={listId}
          placeholder="Research a symbol, e.g. M&M"
          aria-label="Research a symbol"
          className="w-56 pl-8"
          maxLength={20}
          autoComplete="off"
        />
        <datalist id={listId}>
          {suggestions.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      </div>
      <Button type="submit" variant="outline" disabled={!value.trim()}>
        Open report
      </Button>
    </form>
  );
}

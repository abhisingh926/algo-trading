"use client";

import { useState } from "react";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useDebounce } from "@/hooks/use-debounce";
import { useInstruments } from "@/hooks/use-instruments";
import { errorText } from "@/lib/toast";
import { cn } from "@/lib/utils";
import type { Instrument } from "@/types";

interface InstrumentComboboxProps {
  id?: string;
  symbol: string;
  exchange: string;
  onSelect: (instrument: Pick<Instrument, "symbol" | "exchange">) => void;
  disabled?: boolean;
  invalid?: boolean;
}

/** Searchable symbol picker backed by GET /market-data/instruments?search= */
export function InstrumentCombobox({ id, symbol, exchange, onSelect, disabled, invalid }: InstrumentComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search.trim(), 250);
  const { data, isFetching, error } = useInstruments(debounced, open);

  return (
    <Popover open={open} onOpenChange={(o) => setOpen(o)}>
      <PopoverTrigger
        render={
          <Button
            id={id}
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            aria-invalid={invalid}
            disabled={disabled}
            className="w-full justify-between font-normal"
          />
        }
      >
        {symbol ? (
          <span className="truncate">
            <span className="font-medium">{symbol}</span>
            <span className="ml-1.5 text-xs text-muted-foreground">{exchange}</span>
          </span>
        ) : (
          <span className="text-muted-foreground">Search symbol…</span>
        )}
        {isFetching && open ? (
          <Loader2 className="animate-spin opacity-50" />
        ) : (
          <ChevronsUpDown className="opacity-50" />
        )}
      </PopoverTrigger>
      <PopoverContent align="start" className="w-(--anchor-width) min-w-72 p-0">
        <Command shouldFilter={false}>
          <CommandInput value={search} onValueChange={setSearch} placeholder="e.g. RELIANCE, INFY" />
          <CommandList>
            <CommandEmpty>
              {error
                ? errorText(error).title
                : isFetching
                  ? "Searching…"
                  : "No instruments found."}
            </CommandEmpty>
            {data && data.length > 0 ? (
              <CommandGroup>
                {data.map((inst) => {
                  const selected = inst.symbol === symbol && inst.exchange === exchange;
                  return (
                    <CommandItem
                      key={inst.id}
                      value={`${inst.exchange}:${inst.symbol}`}
                      disabled={!inst.is_active}
                      onSelect={() => {
                        onSelect({ symbol: inst.symbol, exchange: inst.exchange });
                        setOpen(false);
                      }}
                    >
                      <Check className={cn("size-4", selected ? "opacity-100" : "opacity-0")} />
                      <span className="font-medium">{inst.symbol}</span>
                      <span className="truncate text-xs text-muted-foreground">{inst.name}</span>
                      <span className="ml-auto text-xs text-muted-foreground">{inst.exchange}</span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            ) : null}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

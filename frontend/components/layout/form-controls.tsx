"use client";

import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface SelectOption<V extends string = string> {
  value: V;
  label: string;
  disabled?: boolean;
}

interface SimpleSelectProps<V extends string> {
  value: V | "";
  onChange: (value: V) => void;
  options: readonly SelectOption<V>[];
  placeholder?: string;
  disabled?: boolean;
  id?: string;
  className?: string;
  size?: "sm" | "default";
  invalid?: boolean;
}

/** Thin wrapper over the shadcn/Base UI select for plain string option lists. */
export function SimpleSelect<V extends string>({
  value,
  onChange,
  options,
  placeholder = "Select…",
  disabled,
  id,
  className,
  size,
  invalid,
}: SimpleSelectProps<V>) {
  return (
    <Select
      items={options}
      value={value === "" ? null : value}
      onValueChange={(v) => {
        if (typeof v === "string") onChange(v as V);
      }}
      disabled={disabled}
    >
      <SelectTrigger id={id} size={size} aria-invalid={invalid} className={cn("w-full", className)}>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent alignItemWithTrigger={false}>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: React.ReactNode;
  error?: string;
  className?: string;
  children: React.ReactNode;
}

export function Field({ label, htmlFor, hint, error, className, children }: FieldProps) {
  return (
    <div className={cn("grid content-start gap-1.5", className)}>
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

/** Parses a numeric text input; returns null when blank or not a finite number. */
export function parseNumber(value: string): number | null {
  const t = value.trim();
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

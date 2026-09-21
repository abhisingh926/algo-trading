"use client";

import { useState } from "react";
import { Loader2, Plus } from "lucide-react";
import { Field, SimpleSelect, type SelectOption } from "@/components/layout/form-controls";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useBrokerStatus, useCreateBroker } from "@/hooks/use-brokers";
import { ApiError } from "@/lib/api";
import type { BrokerEnvironment, BrokerType } from "@/types";

const BROKER_TYPES: BrokerType[] = ["PAPER", "DHAN", "ZERODHA", "FYERS"];
const ENVIRONMENTS: BrokerEnvironment[] = ["PAPER", "SANDBOX", "LIVE"];

export function AddBrokerDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [brokerType, setBrokerType] = useState<BrokerType>("PAPER");
  const [environment, setEnvironment] = useState<BrokerEnvironment>("PAPER");
  const [isDefault, setIsDefault] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const create = useCreateBroker();
  const status = useBrokerStatus();

  const supported = status.data?.supported.find((s) => s.broker_type === brokerType);
  const isPaper = brokerType === "PAPER";

  const typeOptions: SelectOption<BrokerType>[] = BROKER_TYPES.map((t) => {
    const s = status.data?.supported.find((x) => x.broker_type === t);
    return { value: t, label: s && !s.implemented ? `${t} (adapter not implemented)` : t };
  });
  // PAPER brokers only exist in the PAPER environment; real brokers use what the backend supports.
  const envOptions: SelectOption<BrokerEnvironment>[] = ENVIRONMENTS.filter((e) =>
    isPaper ? e === "PAPER" : supported ? supported.environments.includes(e) : e !== "PAPER",
  ).map((e) => ({ value: e, label: e }));

  const reset = () => {
    setName("");
    setBrokerType("PAPER");
    setEnvironment("PAPER");
    setIsDefault(false);
    setErrors({});
  };

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!name.trim()) errs.name = "Name is required";
    if (!envOptions.some((o) => o.value === environment)) errs.environment = "Select an environment";
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    create.mutate(
      { name: name.trim(), broker_type: brokerType, environment, is_default: isDefault },
      {
        onSuccess: () => {
          setOpen(false);
          reset();
        },
        onError: (err) => {
          if (err instanceof ApiError)
            setErrors(Object.fromEntries(err.fieldErrors.map((x) => [x.field, x.message])));
        },
      },
    );
  };

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <Plus /> Add broker account
      </Button>
      <Dialog open={open} onOpenChange={(o) => setOpen(o)}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={onSubmit} noValidate className="grid gap-4">
            <DialogHeader>
              <DialogTitle>Add broker account</DialogTitle>
              <DialogDescription>
                This only registers the account. API keys and tokens are never entered here: they are read from
                backend environment variables.
              </DialogDescription>
            </DialogHeader>
            <Field label="Name" htmlFor="broker-name" error={errors.name}>
              <Input
                id="broker-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Dhan sandbox"
                aria-invalid={!!errors.name}
                maxLength={100}
              />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Broker type" htmlFor="broker-type" error={errors.broker_type}>
                <SimpleSelect
                  id="broker-type"
                  value={brokerType}
                  onChange={(v) => {
                    setBrokerType(v);
                    const sup = status.data?.supported.find((s) => s.broker_type === v);
                    if (v === "PAPER") setEnvironment("PAPER");
                    else if (environment === "PAPER" || (sup && !sup.environments.includes(environment)))
                      setEnvironment("SANDBOX");
                  }}
                  options={typeOptions}
                />
              </Field>
              <Field
                label="Environment"
                htmlFor="broker-env"
                error={errors.environment}
                hint={isPaper ? "Paper brokers always use PAPER" : undefined}
              >
                <SimpleSelect
                  id="broker-env"
                  value={environment}
                  onChange={setEnvironment}
                  options={envOptions}
                  disabled={isPaper}
                  invalid={!!errors.environment}
                />
              </Field>
            </div>
            {!isPaper && supported && !supported.credentials_configured ? (
              <p className="rounded-md border border-warning/40 bg-warning/10 p-2.5 text-xs text-warning">
                No {brokerType} credentials are configured on the backend yet. The account can be added, but the
                connection test will fail until the environment variables are set and the backend restarted.
              </p>
            ) : null}
            {environment === "LIVE" ? (
              <p className="rounded-md border border-loss/40 bg-loss/10 p-2.5 text-xs text-loss">
                LIVE environment connects to real money trading. Orders are still blocked unless every live guard
                passes.
              </p>
            ) : null}
            <div className="flex items-center gap-2.5">
              <Switch id="broker-default" checked={isDefault} onCheckedChange={(c) => setIsDefault(c)} />
              <Label htmlFor="broker-default">Make this the default account</Label>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)} disabled={create.isPending}>
                Cancel
              </Button>
              <Button type="submit" disabled={create.isPending}>
                {create.isPending ? <Loader2 className="animate-spin" /> : null} Add account
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  );
}

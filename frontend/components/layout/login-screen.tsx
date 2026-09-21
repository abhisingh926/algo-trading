"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { CandlestickChart, Loader2 } from "lucide-react";
import { useAuth } from "@/components/layout/auth-provider";
import { Field } from "@/components/layout/form-controls";
import { BackendUnreachable, FullScreenLoader } from "@/components/layout/full-screen";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { authService } from "@/services/auth";

export function LoginScreen() {
  const { state, status, error, retry, signIn } = useAuth();
  const router = useRouter();
  const [wantsRegister, setWantsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    if (state === "open" || state === "authenticated") router.replace("/dashboard");
  }, [state, router]);

  const firstUser = status ? !status.has_users : false;
  const registering = firstUser || (wantsRegister && !!status?.registration_open);

  const submit = useMutation({
    mutationFn: () =>
      registering
        ? authService.register({ email: email.trim(), password, full_name: fullName.trim() })
        : authService.login({ email: email.trim(), password }),
    onSuccess: (token) => {
      toastSuccess(registering ? "Account created" : "Signed in", token.user.email);
      signIn(token);
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setFieldErrors(Object.fromEntries(err.fieldErrors.map((e) => [e.field, e.message])));
      }
      toastError(err);
    },
  });

  if (state === "unreachable") return <BackendUnreachable error={error} onRetry={retry} />;
  if (state !== "unauthenticated") return <FullScreenLoader />;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!email.trim()) errs.email = "Email is required";
    if (registering && !fullName.trim()) errs.full_name = "Full name is required";
    if (registering ? password.length < 8 : password.length === 0)
      errs.password = registering ? "Password must be at least 8 characters" : "Password is required";
    setFieldErrors(errs);
    if (Object.keys(errs).length === 0) submit.mutate();
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2 font-heading text-lg font-semibold">
          <span className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <CandlestickChart className="size-4.5" />
          </span>
          AlgoDesk
        </div>
        <form onSubmit={onSubmit} noValidate className="grid gap-4 rounded-xl border bg-card p-5">
          <div>
            <h1 className="text-base font-semibold">
              {firstUser ? "Create first admin account" : registering ? "Create account" : "Sign in"}
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {firstUser
                ? "No users exist yet. The first registered account becomes the administrator; registration closes afterwards."
                : registering
                  ? "Register a new account on this trading console."
                  : "Sign in to your trading console."}
            </p>
          </div>
          {registering ? (
            <Field label="Full name" htmlFor="full_name" error={fieldErrors.full_name}>
              <Input
                id="full_name"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                aria-invalid={!!fieldErrors.full_name}
              />
            </Field>
          ) : null}
          <Field label="Email" htmlFor="email" error={fieldErrors.email}>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={!!fieldErrors.email}
            />
          </Field>
          <Field
            label="Password"
            htmlFor="password"
            error={fieldErrors.password}
            hint={registering ? "At least 8 characters" : undefined}
          >
            <Input
              id="password"
              type="password"
              autoComplete={registering ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              aria-invalid={!!fieldErrors.password}
            />
          </Field>
          <Button type="submit" size="lg" disabled={submit.isPending}>
            {submit.isPending ? <Loader2 className="animate-spin" /> : null}
            {firstUser ? "Create admin account" : registering ? "Create account" : "Sign in"}
          </Button>
          {!firstUser && status?.registration_open ? (
            <Button
              type="button"
              variant="link"
              className="h-auto p-0"
              onClick={() => {
                setWantsRegister((v) => !v);
                setFieldErrors({});
              }}
            >
              {registering ? "Already have an account? Sign in" : "Need an account? Register"}
            </Button>
          ) : null}
        </form>
      </div>
    </div>
  );
}

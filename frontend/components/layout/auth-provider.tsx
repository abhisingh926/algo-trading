"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { qk } from "@/hooks/query-keys";
import { tokenStore } from "@/lib/api";
import { authService } from "@/services/auth";
import type { AuthStatus, AuthToken, User } from "@/types";

type AuthState =
  | "loading" // resolving /auth/status or /auth/me
  | "unreachable" // backend could not be reached
  | "open" // auth disabled on the backend: no login at all
  | "authenticated"
  | "unauthenticated";

interface AuthContextValue {
  state: AuthState;
  status: AuthStatus | undefined;
  user: User | null;
  error: unknown;
  retry: () => void;
  signIn: (token: AuthToken) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const noopSubscribe = () => () => {};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const qc = useQueryClient();
  const hydrated = useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
  const token = useSyncExternalStore(tokenStore.subscribe, tokenStore.get, () => null);

  const statusQuery = useQuery({
    queryKey: qk.authStatus,
    queryFn: authService.status,
    staleTime: 30_000,
    retry: 1,
  });
  const authEnabled = statusQuery.data?.auth_enabled;

  const meQuery = useQuery({
    queryKey: [...qk.me, token],
    queryFn: authService.me,
    enabled: hydrated && authEnabled === true && !!token,
    staleTime: 5 * 60_000,
  });

  const signIn = useCallback(
    (auth: AuthToken) => {
      qc.setQueryData([...qk.me, auth.access_token], auth.user);
      tokenStore.set(auth.access_token);
      void qc.invalidateQueries({ queryKey: qk.authStatus });
    },
    [qc],
  );

  const signOut = useCallback(() => {
    tokenStore.clear();
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "auth" });
  }, [qc]);

  const refetchStatus = statusQuery.refetch;
  const retry = useCallback(() => void refetchStatus(), [refetchStatus]);

  let state: AuthState;
  if (!hydrated || statusQuery.isPending) state = "loading";
  else if (statusQuery.isError) state = "unreachable";
  else if (!statusQuery.data.auth_enabled) state = "open";
  else if (!token) state = "unauthenticated";
  else if (meQuery.data) state = "authenticated";
  else if (meQuery.isError) state = "unreachable";
  else state = "loading";

  const value = useMemo<AuthContextValue>(
    () => ({
      state,
      status: statusQuery.data,
      user: state === "authenticated" ? (meQuery.data ?? null) : null,
      error: statusQuery.error ?? meQuery.error,
      retry,
      signIn,
      signOut,
    }),
    [state, statusQuery.data, statusQuery.error, meQuery.data, meQuery.error, retry, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/layout/auth-provider";
import { BackendUnreachable, FullScreenLoader } from "@/components/layout/full-screen";
import { HaltedBanner } from "@/components/layout/halted-banner";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";

/** Guards every app page and renders the sidebar + persistent top bar. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const { state, error, retry } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state === "unauthenticated") router.replace("/login");
  }, [state, router]);

  if (state === "unreachable") return <BackendUnreachable error={error} onRetry={retry} />;
  if (state === "loading") return <FullScreenLoader />;
  if (state === "unauthenticated") return <FullScreenLoader label="Redirecting to login…" />;

  return (
    <div className="min-h-screen">
      <Sidebar />
      <div className="flex min-h-screen min-w-0 flex-col lg:pl-56">
        <Topbar />
        <HaltedBanner />
        <main className="mx-auto w-full max-w-[1600px] min-w-0 flex-1 px-3 py-5 sm:px-5">
          {children}
        </main>
      </div>
    </div>
  );
}

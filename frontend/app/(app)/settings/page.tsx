import type { Metadata } from "next";
import { PageHeader } from "@/components/layout/page-header";
import { SettingsView } from "@/components/layout/settings-view";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" description="Account, appearance and read-only system configuration." />
      <SettingsView />
    </>
  );
}

"use client";
import { AicteDashboardView } from "@/components/aicte-dashboard";
import { RoleGuard } from "@/components/role-guard";

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN", "AICTE_OFFICER"]}>
      <AicteDashboardView />
    </RoleGuard>
  );
}

"use client";
import { ConsentsManager } from "@/components/consents-manager";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { useAuth } from "@/lib/auth";

export default function Page() {
  const { t } = useAuth();
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <PageHeader title={t("consent.title")} description={t("consent.intro")} />
      <ConsentsManager />
    </RoleGuard>
  );
}

"use client";
import { FlagQueue } from "@/components/flag-queue";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { useAuth } from "@/lib/auth";

export default function Page() {
  const { t } = useAuth();
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <PageHeader title={t("inst.flags.title")} description={t("inst.flags.intro")} />
      <FlagQueue mode="institution" />
    </RoleGuard>
  );
}

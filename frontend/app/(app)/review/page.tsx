"use client";
import { FlagQueue } from "@/components/flag-queue";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { useAuth } from "@/lib/auth";

export default function Page() {
  const { t } = useAuth();
  return (
    <RoleGuard roles={["AICTE_ADMIN", "AICTE_OFFICER"]}>
      <PageHeader title={t("review.title")} description={t("review.intro")} />
      <FlagQueue mode="aicte" />
    </RoleGuard>
  );
}

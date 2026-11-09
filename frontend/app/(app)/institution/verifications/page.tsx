"use client";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { VerificationList } from "@/components/verification-list";
import { useAuth } from "@/lib/auth";

export default function Page() {
  const { t } = useAuth();
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <PageHeader title={t("ver.title")} description={t("ver.intro")} />
      <VerificationList />
    </RoleGuard>
  );
}

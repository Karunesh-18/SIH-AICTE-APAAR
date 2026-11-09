"use client";
import { PageHeader } from "@/components/page-header";
import { RoleGuard } from "@/components/role-guard";
import { VerifierWorkspace } from "@/components/verifier-workspace";
import { useAuth } from "@/lib/auth";

export default function Page() {
  const { t } = useAuth();
  return (
    <RoleGuard roles={["VERIFIER"]}>
      <PageHeader title={t("vr.title")} description={t("vr.intro")} />
      <VerifierWorkspace />
    </RoleGuard>
  );
}

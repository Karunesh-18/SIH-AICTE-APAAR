"use client";
import { useParams } from "next/navigation";
import { CertificateRecord } from "@/components/certificate-record";
import { RoleGuard } from "@/components/role-guard";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF", "AICTE_ADMIN", "AICTE_OFFICER"]}>
      <CertificateRecord id={id} />
    </RoleGuard>
  );
}

"use client";
import { useParams } from "next/navigation";
import { FlagDetailView } from "@/components/flag-detail";
import { RoleGuard } from "@/components/role-guard";

export default function Page() {
  const { id } = useParams<{ id: string }>();
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN", "INSTITUTION_STAFF"]}>
      <FlagDetailView id={id} backHref="/institution/flags" />
    </RoleGuard>
  );
}

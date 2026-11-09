"use client";
import { RoleGuard } from "@/components/role-guard";
import { UsersManager } from "@/components/users-manager";

export default function Page() {
  return (
    <RoleGuard roles={["AICTE_ADMIN"]}>
      <UsersManager mode="admin" />
    </RoleGuard>
  );
}

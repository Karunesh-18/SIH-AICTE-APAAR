"use client";
import { RoleGuard } from "@/components/role-guard";
import { UsersManager } from "@/components/users-manager";

export default function Page() {
  return (
    <RoleGuard roles={["INSTITUTION_ADMIN"]}>
      <UsersManager mode="staff" />
    </RoleGuard>
  );
}

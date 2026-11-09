"use client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

/** Plain yes/no confirmation for actions that cannot be undone (withdraw, revoke, tamper demo). */
export function ConfirmDialog({ open, title, body, confirmLabel, cancelLabel, pending, onConfirm, onClose }: {
  open: boolean; title: string; body: string; confirmLabel: string; cancelLabel: string;
  pending?: boolean; onConfirm: () => void; onClose: () => void;
}) {
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{body}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>{cancelLabel}</Button>
          <Button variant="destructive" disabled={pending} onClick={onConfirm}>{confirmLabel}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

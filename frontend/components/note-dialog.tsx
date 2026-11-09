"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { noteError } from "@/lib/review";

type Props = {
  open: boolean; title: string; label: string; confirmLabel: string; description?: string;
  pending?: boolean; destructive?: boolean; t: (k: string) => string;
  onSubmit: (note: string) => void; onClose: () => void;
};

/** A dialog that cannot be confirmed without a note (flag actions and withdraw reasons). */
export function NoteDialog({ open, title, label, confirmLabel, description, pending, destructive, t, onSubmit, onClose }: Props) {
  const [note, setNote] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const close = () => { setNote(""); setErr(null); onClose(); };
  const submit = () => {
    const e = noteError(note);
    setErr(e);
    if (!e) onSubmit(note.trim());
  };
  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) close(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t(title)}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="note-field">{t(label)}</Label>
          <Textarea id="note-field" rows={4} value={note} aria-invalid={!!err}
                    onChange={(e) => { setNote(e.target.value); if (err) setErr(null); }} />
          {err && <p role="alert" className="text-sm text-status-excess">{t(err)}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={close}>{t("dialog.cancel")}</Button>
          <Button variant={destructive ? "destructive" : "default"} disabled={pending} onClick={submit}>{t(confirmLabel)}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

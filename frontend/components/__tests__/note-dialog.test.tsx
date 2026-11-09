// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { NoteDialog } from "../note-dialog";

afterEach(cleanup);
const t = (k: string) => k;
const setup = (over = {}) => {
  const onSubmit = vi.fn();
  const onClose = vi.fn();
  render(<NoteDialog open title="flag.action.resolve" label="flag.note" confirmLabel="flag.action.resolve" t={t}
                     onSubmit={onSubmit} onClose={onClose} {...over} />);
  return { onSubmit, onClose };
};

describe("NoteDialog", () => {
  it("blocks an empty note and shows the error", () => {
    const { onSubmit } = setup();
    fireEvent.click(screen.getByRole("button", { name: "flag.action.resolve" }));
    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toBe("flag.note.required");
  });
  it("blocks a whitespace-only note", () => {
    const { onSubmit } = setup();
    fireEvent.change(screen.getByLabelText("flag.note"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "flag.action.resolve" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it("submits the trimmed note", () => {
    const { onSubmit } = setup();
    fireEvent.change(screen.getByLabelText("flag.note"), { target: { value: "  checked  " } });
    fireEvent.click(screen.getByRole("button", { name: "flag.action.resolve" }));
    expect(onSubmit).toHaveBeenCalledWith("checked");
  });
  it("cancel closes", () => {
    const { onClose } = setup();
    fireEvent.click(screen.getByRole("button", { name: "dialog.cancel" }));
    expect(onClose).toHaveBeenCalled();
  });
  it("disables confirm while pending", () => {
    setup({ pending: true });
    expect((screen.getByRole("button", { name: "flag.action.resolve" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

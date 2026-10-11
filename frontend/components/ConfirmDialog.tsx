"use client";

import * as AlertDialog from "@radix-ui/react-alert-dialog";

/**
 * "Are you sure?" for actions that can't be undone (e.g. Cancel order).
 * Radix handles the hard accessibility parts: focus moves into the dialog,
 * Esc closes it, and screen readers announce it as an alert.
 */
export function ConfirmDialog({
  trigger,
  title,
  text,
  confirmLabel,
  cancelLabel = "Keep it",
  onConfirm,
}: {
  trigger: React.ReactNode;
  title: string;
  text: string;
  confirmLabel: string;
  cancelLabel?: string;
  onConfirm: () => void;
}) {
  return (
    <AlertDialog.Root>
      <AlertDialog.Trigger asChild>{trigger}</AlertDialog.Trigger>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className="fixed inset-0 z-40 bg-ink/40" />
        <AlertDialog.Content className="panel fixed left-1/2 top-1/2 z-50 flex w-[min(440px,calc(100vw-32px))] -translate-x-1/2 -translate-y-1/2 flex-col gap-3">
          <AlertDialog.Title className="text-[22px] font-bold tracking-[-0.03em]">{title}</AlertDialog.Title>
          <AlertDialog.Description className="text-muted">{text}</AlertDialog.Description>
          <div className="mt-2 flex flex-wrap justify-end gap-2.5">
            <AlertDialog.Cancel className="btn btn-white">{cancelLabel}</AlertDialog.Cancel>
            <AlertDialog.Action className="btn btn-black" onClick={onConfirm}>
              {confirmLabel}
            </AlertDialog.Action>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}

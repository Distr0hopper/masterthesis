import { useEffect, useState, type ReactNode } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog.tsx';
import { Button } from '@/components/ui/button.tsx';

/**
 * An opt-in for also deleting a second, linked entity - the draft <-> workflow link is
 * deletable from either end, and neither end may silently destroy the other.
 */
interface LinkedDeleteOption {
  /** Checkbox copy. Say what survives when it is left unchecked, not just what it deletes. */
  label: ReactNode;
  /** Confirm button label while ticked. */
  confirmLabel?: string;
}

interface ConfirmDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: ReactNode;
  /** Omit when nothing is linked - the checkbox is then not rendered at all. */
  linkedOption?: LinkedDeleteOption;
  /** Receives whether the linked entity should go too; always false without a linkedOption. */
  onConfirm: (deleteLinked: boolean) => void;
  isPending: boolean;
  /** Extra block content under the description, e.g. a usage warning. */
  children?: ReactNode;
  /** The delete isn't possible at all - only a Close button is offered; children say why. */
  blocked?: boolean;
  /** The alternative offered while blocked, e.g. deprecating instead of deleting. Closes this dialog. */
  blockedAlternative?: { label: string; onSelect: () => void };
  /** Confirm button label, when the plain "Delete" undersells what goes (e.g. "Delete and unpublish 2"). */
  confirmLabel?: string;
}

export function ConfirmDeleteDialog({
  open,
  onOpenChange,
  title,
  description,
  linkedOption,
  onConfirm,
  isPending,
  children,
  blocked = false,
  blockedAlternative,
  confirmLabel = 'Delete',
}: ConfirmDeleteDialogProps) {
  const [deleteLinked, setDeleteLinked] = useState(false);

  // a dialog instance outlives one delete - reopening it must not inherit the last tick
  useEffect(() => {
    if (open) setDeleteLinked(false);
  }, [open]);

  // never report a cascade the caller did not offer, even if a stale tick survived
  const cascade = linkedOption !== undefined && deleteLinked;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {/* outside DialogDescription for the same reason as the checkbox below */}
        {children}

        {linkedOption && !blocked && (
          // outside DialogDescription on purpose: that renders a <p>, which cannot
          // legally contain a label or an input
          <label className="flex items-start gap-2 rounded-md border border-slate-200 p-3 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={deleteLinked}
              onChange={(e) => setDeleteLinked(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-input accent-jmu-blue-800"
            />
            <span>{linkedOption.label}</span>
          </label>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            {blocked ? 'Close' : 'Cancel'}
          </Button>
          {blocked && blockedAlternative && (
            <Button
              type="button"
              onClick={() => {
                onOpenChange(false);
                blockedAlternative.onSelect();
              }}
            >
              {blockedAlternative.label}
            </Button>
          )}
          {!blocked && (
            <Button type="button" variant="destructive" onClick={() => onConfirm(cascade)} disabled={isPending}>
              {isPending ? 'Deleting...' : cascade ? (linkedOption?.confirmLabel ?? 'Delete both') : confirmLabel}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

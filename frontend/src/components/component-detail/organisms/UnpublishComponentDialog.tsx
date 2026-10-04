import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog.tsx';
import { Button } from '@/components/ui/button.tsx';
import { PublicAncestors } from '@/components/common/PublicAncestors';
import {
  isRetractBlocked,
  ownPublishedAncestors,
  useComponentImpact,
  useUnpublishComponent,
  type ComponentDetailDisplayModel,
} from '@/api/components';
import { canDeprecate, getLink } from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';

interface UnpublishComponentDialogProps {
  model: ComponentDetailDisplayModel;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** opens the deprecate dialog - offered when unpublishing is blocked */
  onDeprecateInstead: () => void;
}

/**
 * Unpublishing shows its consequences before the click: the public workflows running this
 * version, at any depth. Other users' ones block it - it would break their workflow - and
 * the user's own become drafts along with it. The server enforces the same rule; its 409
 * only shows up if a parent was published between opening this dialog and confirming.
 */
export function UnpublishComponentDialog({ model, open, onOpenChange, onDeprecateInstead }: UnpublishComponentDialogProps) {
  const { mutate: unpublish, isPending } = useUnpublishComponent();
  const { data: impact, isLoading } = useComponentImpact(getLink(model._links, 'impact'), open);

  const blocked = isRetractBlocked(impact);
  const ownCount = impact ? ownPublishedAncestors(impact).length : 0;
  // private drafts of other users break nothing public - publishing them stops later anyway
  const otherDrafts = impact?.hiddenWorkflowCount ?? 0;

  const handleConfirm = () => {
    unpublish(
      { link: getLink(model._links, 'unpublish')!, unpublishParents: ownCount > 0 },
      {
        onSuccess: () => {
          onOpenChange(false);
          toast.success(
            ownCount > 0
              ? `${model.kindDisplay} unpublished, along with ${ownCount} of your workflows`
              : `${model.kindDisplay} unpublished`,
          );
        },
        onError: (error) => toast.error(getErrorMessage(error)),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{blocked ? `${model.name} cannot be unpublished` : `Unpublish ${model.name}?`}</DialogTitle>
          <DialogDescription>
            {blocked ? 'Public workflows that run this version would break.' : 'Only you will be able to see it.'}
          </DialogDescription>
        </DialogHeader>

        {isLoading && <p className="text-sm text-slate-500">Checking where this version is used...</p>}
        {impact && <PublicAncestors impact={impact} verb="Unpublishing" />}
        {otherDrafts > 0 && (
          <p className="text-sm text-slate-600">
            Also used in {otherDrafts} private draft{otherDrafts === 1 ? '' : 's'} of another user.
          </p>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isPending}>
            {blocked ? 'Close' : 'Cancel'}
          </Button>
          {blocked && canDeprecate(model._links) && (
            <Button
              type="button"
              onClick={() => {
                onOpenChange(false);
                onDeprecateInstead();
              }}
            >
              Deprecate instead
            </Button>
          )}
          {!blocked && (
            <Button type="button" onClick={handleConfirm} disabled={isPending || isLoading}>
              {isPending ? 'Unpublishing...' : ownCount > 0 ? `Unpublish all ${ownCount + 1}` : 'Unpublish'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

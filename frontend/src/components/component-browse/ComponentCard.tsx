import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { PenLine } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { ComponentFavoriteButton } from '@/components/ComponentFavoriteButton';
import { ComponentSource, ComponentStatus, type ComponentDisplayModel } from '@/api/components';
import { canDelete, canFavorite } from '@/api/permissions';
import { KIND_ROUTES, ROUTES } from '@/lib/routes';
import { DomainBadges } from '@/components/common/DomainBadges';

interface ComponentCardProps {
  component: ComponentDisplayModel;
  backTo?: string;
  /** an editing surface (My Workflows) - offer "Edit in Workflow Builder" where possible */
  showBuilderLink?: boolean;
  /** show which kind it is - for lists mixing tools and workflows */
  showKind?: boolean;
  actions?: ReactNode;
}

/** One card for either kind - only the footer line and the builder link differ. */
export function ComponentCard({ component, backTo, showBuilderLink = false, showKind = false, actions }: ComponentCardProps) {
  // Three separate conditions, all required:
  //  - showBuilderLink: this surface is an editing one (My Workflows), not the browse list
  //  - source/draftId:  it came from the builder, and that draft still exists (the FK is
  //                     ON DELETE SET NULL, so a deleted draft leaves the workflow intact
  //                     but no longer editable)
  //  - canDelete:       you own it. Drafts are owner-scoped, so the link would 404 for
  //                     anyone else. `canDelete` is this codebase's ownership signal - the
  //                     API only emits that link for the owner.
  const builderDraftId =
    showBuilderLink &&
    component.kind === 'workflow' &&
    component.source === ComponentSource.WORKFLOW_BUILDER &&
    canDelete(component._links)
      ? component.draftId
      : null;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-wrap items-center gap-2">
            {showKind && (
              <Badge variant="outline" className="w-fit">
                {component.kindDisplay}
              </Badge>
            )}
            {component.status !== ComponentStatus.PUBLISHED && (
              <Badge variant="secondary" className="w-fit">
                {component.statusDisplay}
              </Badge>
            )}
            <DomainBadges domains={component.domains} />
          </div>

          {canFavorite(component._links) && (
            <ComponentFavoriteButton links={component._links!} isFavorite={component.isFavorite} />
          )}
        </div>

        <h3 className="font-mono text-lg font-bold text-slate-900">{component.name}</h3>

        {component.description && <p className="line-clamp-2 text-sm text-slate-500">{component.description}</p>}

        <div className="flex items-center justify-between border-t pt-3 text-sm text-slate-500">
          <span>{component.kind === 'workflow' ? `${component.stepCount} steps` : component.authorDisplay}</span>
          <span>{component.createdAtDisplay}</span>
        </div>

        {/* stacked, not side by side: "Edit in Workflow Builder" is too long to sit
            next to View in a three-column card grid without truncating */}
        <div className="flex flex-col gap-2">
          <Button asChild className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
            <Link
              to={KIND_ROUTES[component.kind].detail(component.id)}
              state={{ from: backTo ?? KIND_ROUTES[component.kind].browse }}
            >
              View
            </Link>
          </Button>

          {builderDraftId && (
            <Button asChild variant="outline" className="w-full" title="Open the draft this was published from">
              <Link to={ROUTES.builderWorkflow(builderDraftId)}>
                <PenLine className="h-4 w-4" />
                Edit in Workflow Builder
              </Link>
            </Button>
          )}

          {actions}
        </div>
      </CardContent>
    </Card>
  );
}

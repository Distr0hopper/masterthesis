import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { PenLine } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { ComponentFavoriteButton } from '@/components/ComponentFavoriteButton';
import { ComponentStatus, type ComponentDisplayModel } from '@/api/components';
import { canFavorite } from '@/api/permissions';
import { KIND_ROUTES, ROUTES } from '@/lib/routes';
import { DomainBadges } from '@/components/common/DomainBadges';
import { KindBadge } from '@/components/common/KindBadge';
import { VersionSwitcher } from '@/components/common/VersionSwitcher';
import { editableBuilderDraftId } from '@/lib/builderDraft';

interface ComponentCardProps {
  component: ComponentDisplayModel;
  backTo?: string;
  /** an editing surface (My Workflows) - offer "Edit in Workflow Builder" where possible */
  showBuilderLink?: boolean;
  actions?: ReactNode;
}

/** One card for either kind - only the kind snippet, a workflow's step count and the builder link differ. */
export function ComponentCard({ component, backTo, showBuilderLink = false, actions }: ComponentCardProps) {

  // only on an editing surface (My Workflows), not the browse list
  const builderDraftId = showBuilderLink ? editableBuilderDraftId(component) : null;

  return (
    // four rows shared with the other cards of a grid row (subgrid): content, footer, View,
    // extra actions - so View lines up even when one card has more actions than another
    <Card className="row-span-4 grid grid-rows-subgrid gap-0">
      <CardContent className="row-span-4 grid grid-rows-subgrid gap-0 pt-6">
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div className="flex flex-wrap items-center gap-2">
              <KindBadge kind={component.kind} />
              {component.status !== ComponentStatus.PUBLISHED && (
                <Badge variant="secondary" className="w-fit" title={component.statusHint ?? undefined}>
                  {component.statusDisplay}
                </Badge>
              )}
              <DomainBadges domains={component.domains} />
            </div>

            {canFavorite(component._links) && (
              <ComponentFavoriteButton links={component._links!} isFavorite={component.isFavorite} />
            )}
          </div>

          <div>
            <h3 className="font-mono text-lg font-bold text-slate-900">{component.name}</h3>
            {/* always its own line under the name - a long name never pushes it beside or below */}
            {component.versionCount !== null && component.versionCount > 1 ? (
              // with other versions, the version opens them
              <VersionSwitcher
                componentId={component.id}
                kind={component.kind}
                version={component.version}
                versionCount={component.versionCount}
                backTo={backTo}
                className="-ml-1"
              />
            ) : (
              <p className="text-sm text-slate-400">v{component.version}</p>
            )}
          </div>

          {component.description && <p className="line-clamp-2 text-sm text-slate-500">{component.description}</p>}
        </div>

        <div className="mt-3 flex items-center justify-between border-t pt-3 text-sm text-slate-500">
          <span>
            {component.authorDisplay}
            {component.kind === 'workflow' &&
              ` · ${component.stepCount} step${component.stepCount === 1 ? '' : 's'}`}
          </span>
          <span>{component.createdAtDisplay}</span>
        </div>

        <Button asChild className="mt-3 w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
          <Link
            to={KIND_ROUTES[component.kind].detail(component.id)}
            state={{ from: backTo ?? KIND_ROUTES[component.kind].browse }}
          >
            View
          </Link>
        </Button>

        <div className="mt-2 flex flex-col gap-2 empty:mt-0">
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

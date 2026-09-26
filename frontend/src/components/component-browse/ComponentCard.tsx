import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { ComponentFavoriteButton } from '@/components/ComponentFavoriteButton';
import { ComponentStatus, type ComponentDisplayModel } from '@/api/components';
import { canFavorite } from '@/api/permissions';
import { ROUTES } from '@/lib/routes';
import { DomainBadges } from '@/components/common/DomainBadges';

interface ComponentCardProps {
  component: ComponentDisplayModel;
  backTo?: string;
  actions?: ReactNode;
}

export function ComponentCard({ component, backTo = ROUTES.components, actions }: ComponentCardProps) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6">
        <div className="flex items-center justify-between">
          <div className="flex flex-wrap items-center gap-2">
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

        {component.description && (
          <p className="line-clamp-2 text-sm text-slate-500">{component.description}</p>
        )}

        <div className="flex items-center justify-between border-t pt-3 text-sm text-slate-500">
          <span>{component.authorDisplay}</span>
          <span>{component.createdAtDisplay}</span>
        </div>

        <Button asChild className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
          <Link to={ROUTES.componentDetail(component.id)} state={{ from: backTo }}>
            View
          </Link>
        </Button>

        {actions}
      </CardContent>
    </Card>
  );
}

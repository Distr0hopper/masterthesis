import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { FavoriteButton } from '@/components/FavoriteButton';
import { getDomainBadgeStyle, useDomains, type ComponentDisplayModel } from '@/api/components';
import { canFavorite } from '@/api/permissions';
import { ROUTES } from '@/lib/routes';

interface ComponentCardProps {
  component: ComponentDisplayModel;
  actions?: ReactNode;
}

export function ComponentCard({ component, actions }: ComponentCardProps) {
  const { data: domains } = useDomains();
  const domainBadgeStyle = domains ? getDomainBadgeStyle(component.domain, domains) : undefined;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6">
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="w-fit" style={domainBadgeStyle}>
            {component.domainDisplay}
          </Badge>

          {canFavorite(component._links) && <FavoriteButton componentId={component.id} isFavorite={component.isFavorite} />}
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
          <Link to={ROUTES.componentDetail(component.id)}>View</Link>
        </Button>

        {actions}
      </CardContent>
    </Card>
  );
}

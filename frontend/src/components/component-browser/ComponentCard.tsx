import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { getDomainColor, useDomains, type ComponentDisplayModel } from '@/api/components';

interface ComponentCardProps {
  component: ComponentDisplayModel;
  actions?: ReactNode;
}

export function ComponentCard({ component, actions }: ComponentCardProps) {
  const { data: domains } = useDomains();
  const domainColor = domains ? getDomainColor(component.domain, domains) : undefined;

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-6">
        <Badge
          variant="outline"
          className="w-fit"
          style={domainColor ? { borderColor: domainColor, color: domainColor } : undefined}
        >
          {component.domainDisplay}
        </Badge>

        <h3 className="font-mono text-lg font-bold text-slate-900">{component.name}</h3>

        {component.description && (
          <p className="line-clamp-2 text-sm text-slate-500">{component.description}</p>
        )}

        <div className="flex items-center justify-between border-t pt-3 text-sm text-slate-500">
          <span>{component.authorDisplay}</span>
          <span>{component.createdAtDisplay}</span>
        </div>

        <Button asChild className="w-full bg-jmu-blue-800 hover:bg-jmu-blue-800/90">
          <Link to={`/components/${component.id}`}>View</Link>
        </Button>

        {actions}
      </CardContent>
    </Card>
  );
}

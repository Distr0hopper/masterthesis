import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import type { LatestAdditionItem } from './latestAdditionItem';

const BADGE_CLASSNAME: Record<LatestAdditionItem['kind'], string> = {
  tool: 'border-emerald-300 text-emerald-700',
  workflow: 'border-jmu-blue-300 text-jmu-blue-700',
};

interface LatestAdditionsProps {
  items: LatestAdditionItem[];
  isLoading: boolean;
}

export function LatestAdditions({ items, isLoading }: LatestAdditionsProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-slate-900">Latest additions</h2>
      <Card className="mt-3">
        <CardContent className="divide-y p-0">
          {isLoading ? (
            <p className="p-6 text-sm text-slate-500">Loading...</p>
          ) : items.length === 0 ? (
            <p className="p-6 text-sm text-slate-500">Nothing uploaded yet.</p>
          ) : (
            items.map((item) => (
              <Link
                key={item.id}
                to={item.href}
                className="flex items-center justify-between px-6 py-4 hover:bg-slate-50"
              >
                <div>
                  <p className="font-mono font-semibold text-slate-900">{item.name}</p>
                  <p className="mt-0.5 text-sm text-slate-500">{item.subtitle}</p>
                </div>
                <Badge variant="outline" className={BADGE_CLASSNAME[item.kind]}>
                  {item.badgeLabel}
                </Badge>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

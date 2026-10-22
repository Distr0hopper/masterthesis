import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { DomainBadges } from '@/components/common/DomainBadges';
import { KindBadge } from '@/components/common/KindBadge';
import type { LatestAdditionItem } from './latestAdditionItem';

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
                className="flex items-center justify-between gap-4 px-6 py-4 hover:bg-slate-50"
              >
                <div className="min-w-0">
                  <p className="font-mono font-semibold text-slate-900">{item.name}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <DomainBadges domains={item.domains} />
                    <span className="text-sm text-slate-500">{item.createdAtDisplay}</span>
                  </div>
                </div>
                <KindBadge kind={item.kind} className="shrink-0" />
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

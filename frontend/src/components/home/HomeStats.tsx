import { Card, CardContent } from '@/components/ui/card.tsx';
import type { StatsDto } from '@/api/stats';

interface HomeStatsProps {
  stats: StatsDto | undefined;
}

const STAT_ITEMS: { label: string; getValue: (stats: StatsDto) => number }[] = [
  { label: 'Tools published', getValue: (stats) => stats.toolsPublished },
  { label: 'Workflows published', getValue: (stats) => stats.workflowsPublished },
  { label: 'Contributors', getValue: (stats) => stats.contributors },
];

export function HomeStats({ stats }: HomeStatsProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      {STAT_ITEMS.map((item) => (
        <Card key={item.label}>
          <CardContent className="pt-6">
            <p className="text-3xl font-bold text-jmu-blue-800">{stats ? item.getValue(stats) : '—'}</p>
            <p className="mt-1 text-sm text-slate-500">{item.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

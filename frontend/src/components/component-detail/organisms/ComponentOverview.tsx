import type { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { cn } from '@/lib/utils';
import type { ComponentDetailDisplayModel } from '@/api/components';
import { ParameterList } from '../common/ParameterList';

interface StatCardProps {
  label: string;
  value: ReactNode;
  valueClassName?: string;
}

function StatCard({ label, value, valueClassName }: StatCardProps) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-slate-500">{label}</p>
        <p className={cn('font-bold text-slate-900', valueClassName)}>{value}</p>
      </CardContent>
    </Card>
  );
}

interface ComponentOverviewProps {
  model: ComponentDetailDisplayModel;
}

export function ComponentOverview({ model }: ComponentOverviewProps) {
  const stats: StatCardProps[] = [
    { label: 'CWL Type', value: model.cwlType ?? '—', valueClassName: 'font-mono' },
    { label: 'Parameters', value: model.parameters.length, valueClassName: 'text-xl' },
    { label: 'Inputs', value: model.inputs.length, valueClassName: 'text-xl' },
    { label: 'Outputs', value: model.outputs.length, valueClassName: 'text-xl' },
  ];

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.label} {...stat} />
        ))}
      </div>

      {model.description && (
        <div>
          <h3 className="font-semibold text-slate-900">Description</h3>
          <p className="mt-1 text-sm text-slate-600">{model.description}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <ParameterList title="INPUTS" parameters={model.inputs} />
        <ParameterList title="OUTPUTS" parameters={model.outputs} />
      </div>
    </div>
  );
}

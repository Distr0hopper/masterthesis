import { Card, CardContent } from '@/components/ui/card.tsx';

const STANDARDS = [
  { label: 'DEFINITION', value: 'CWL v1.2' },
  { label: 'CONTAINERS', value: 'Docker' },
  { label: 'SOURCE', value: 'GitHub' },
  { label: 'IDENTIFIERS', value: 'DOI' },
];

export function StandardsIntegrations() {
  return (
    <div className="mt-10">
      <h2 className="text-lg font-semibold text-slate-900">Standards &amp; integrations</h2>
      <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-5">
        {STANDARDS.map((standard) => (
          <Card key={standard.label}>
            <CardContent className="pt-6">
              <p className="text-xs font-semibold tracking-wide text-slate-400">{standard.label}</p>
              <p className="mt-1 font-semibold text-slate-900">{standard.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

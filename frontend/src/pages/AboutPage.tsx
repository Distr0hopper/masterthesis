import { ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';

const SECTIONS = [
  {
    label: 'PROBLEM',
    text: 'Domain scientists re-implement the same analysis scripts across projects, with limited reusability and no cross-domain integration between Movement Ecology and Earth Observation pipelines.',
  },
  {
    label: 'METHOD',
    text: 'Analysis steps are wrapped as CWL CommandLineTools — either uploaded manually or packaged automatically from a MoveApps GitHub repository — and chained into reusable, versioned Workflows.',
  },
  {
    label: 'OUTCOME',
    text: 'A searchable, cross-domain registry of Components and Workflows that researchers can browse, inspect, and reuse without re-implementing scripts.',
  },
];

const STANDARDS = ['CWL v1.2', 'Docker', 'MoveApps', 'GitHub', 'DOI'];

export default function AboutPage() {
  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">About the Component Repository</h1>
      <p className="mt-3 max-w-2xl text-slate-500">
        A Master's thesis project at the Chair of Computer Science II, Julius-Maximilians-Universität Würzburg: a
        repository for component-based workflow engineering using the Common Workflow Language.
      </p>

      <Card className="mt-6">
        <CardContent className="divide-y pt-6">
          {SECTIONS.map((section) => (
            <div key={section.label} className="py-4 first:pt-0 last:pb-0">
              <h3 className="text-xs font-semibold tracking-wide text-jmu-blue-800">{section.label}</h3>
              <p className="mt-2 text-slate-600">{section.text}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <h2 className="mt-8 text-lg font-semibold text-slate-900">SOS Project</h2>
      <Card className="mt-3">
        <CardContent className="flex flex-col gap-3 pt-6">
          <p className="text-slate-600">
            This repository is developed in the context of the{' '}
            <span className="font-semibold text-slate-900">SOS — Scalable Open Science</span> project, funded by the
            Deutsche Forschungsgemeinschaft (DFG). The SOS project investigates infrastructure for reproducible,
            interoperable scientific workflows across research domains.
          </p>
          <a
            href="https://dfg-sos.de"
            target="_blank"
            rel="noreferrer"
            className="inline-flex w-fit items-center gap-1 text-jmu-blue-800 hover:underline"
          >
            <ExternalLink className="h-4 w-4" /> dfg-sos.de
          </a>
        </CardContent>
      </Card>

      <h2 className="mt-8 text-lg font-semibold text-slate-900">Standards used</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {STANDARDS.map((standard) => (
          <Badge key={standard} variant="outline" className="border-jmu-blue-300 text-jmu-blue-800">
            {standard}
          </Badge>
        ))}
      </div>

      <h2 className="mt-8 text-lg font-semibold text-slate-900">Contact</h2>
      <p className="mt-3 text-slate-600">
        Chair of Computer Science II · Julius-Maximilians-Universität Würzburg ·{' '}
        <a href="mailto:lorenz.gruber@uni-wuerzburg.de" className="text-jmu-blue-800 hover:underline">
            lorenz.gruber@uni-wuerzburg.de
        </a>
      </p>
    </div>
  );
}

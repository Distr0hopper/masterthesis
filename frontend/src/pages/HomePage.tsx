import { Link } from 'react-router-dom';
import { GitMerge, LayoutGrid, Upload, Workflow } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { componentTransformer, useLatestComponents } from '@/api/components';
import { useStats } from '@/api/stats';

// no backend tagging concept exists - purely decorative, matching the mockup
const TAGS = [
  'CWL',
  'CommandLineTool',
  'Workflow',
  'Docker',
  'MoveApps',
  'Movement Ecology',
  'Earth Observation',
];

const STANDARDS = [
  { label: 'DEFINITION', value: 'CWL v1.2' },
  { label: 'CONTAINERS', value: 'Docker' },
  { label: 'SOURCE', value: 'GitHub' },
  { label: 'IDENTIFIERS', value: 'DOI' },
];

const FIND_CONTENT_LINKS = [
  { label: 'Browse Components', to: '/browse', icon: LayoutGrid },
  { label: 'Browse Workflows', to: '/builder', icon: Workflow },
  { label: 'Upload a Component', to: '/upload', icon: Upload },
  { label: 'Build a Workflow', to: '/builder', icon: GitMerge },
];

export default function HomePage() {
  const { data: stats } = useStats();
  const { data: latest, isLoading: isLoadingLatest } = useLatestComponents(6);
  const latestDisplayModels = componentTransformer.toListDisplayModels(latest ?? []);

  return (
    <div className="-mx-4 -mt-8">
      <section className="relative left-1/2 right-1/2 -mx-[50vw] w-screen bg-[radial-gradient(ellipse_at_top,_var(--jmu-blue-500)_0%,_var(--jmu-blue-600)_55%)] px-4 py-16 text-white">
        <div className="mx-auto max-w-6xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-jmu-blue-200">
            Chair of Computer Science II — JMU Würzburg
          </p>
          <h1 className="mt-3 max-w-2xl text-4xl font-bold leading-tight">
            A repository for reusable, CWL-wrapped research components
          </h1>
          <p className="mt-4 max-w-2xl text-jmu-blue-100">
            Researchers in Movement Ecology and Earth Observation upload analysis steps once, wrap them as Common
            Workflow Language CommandLineTools, and chain them into reusable Workflows — instead of re-implementing
            scripts or hand-packaging MoveApps repositories.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Button asChild className="bg-white text-jmu-blue-600 hover:bg-jmu-blue-50">
              <Link to="/browse">Browse Components</Link>
            </Button>
            <Button asChild variant="outline" className="border-white bg-transparent text-white hover:bg-white/10">
              <Link to="/builder">Browse Workflows</Link>
            </Button>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 py-8">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="pt-6">
              <p className="text-3xl font-bold text-jmu-blue-800">{stats?.componentsPublished ?? '—'}</p>
              <p className="mt-1 text-sm text-slate-500">Components published</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-3xl font-bold text-jmu-blue-800">{stats?.workflowsComposed ?? '—'}</p>
              <p className="mt-1 text-sm text-slate-500">Workflows composed</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <p className="text-3xl font-bold text-jmu-blue-800">{stats?.contributors ?? '—'}</p>
              <p className="mt-1 text-sm text-slate-500">Contributors</p>
            </CardContent>
          </Card>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-slate-900">Latest additions</h2>
            <Card className="mt-3">
              <CardContent className="divide-y p-0">
                {isLoadingLatest ? (
                  <p className="p-6 text-sm text-slate-500">Loading...</p>
                ) : latestDisplayModels.length === 0 ? (
                  <p className="p-6 text-sm text-slate-500">No components yet.</p>
                ) : (
                  latestDisplayModels.map((component) => (
                    <Link
                      key={component.id}
                      to={`/components/${component.id}`}
                      className="flex items-center justify-between px-6 py-4 hover:bg-slate-50"
                    >
                      <div>
                        <p className="font-mono font-semibold text-slate-900">{component.name}</p>
                        <p className="mt-0.5 text-sm text-slate-500">
                          {component.domainDisplay} · {component.createdAtDisplay}
                        </p>
                      </div>
                      <Badge variant="outline" className="border-emerald-300 text-emerald-700">
                        Component
                      </Badge>
                    </Link>
                  ))
                )}
              </CardContent>
            </Card>
          </div>

          <div className="flex flex-col gap-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Find content</h2>
              <div className="mt-3 grid grid-cols-2 gap-3">
                {FIND_CONTENT_LINKS.map((link) => (
                  <Link key={link.label} to={link.to}>
                    <Card className="h-full transition-colors hover:border-jmu-blue-300">
                      <CardContent className="flex flex-col gap-2 pt-6">
                        <link.icon className="h-5 w-5 text-jmu-blue-800" />
                        <p className="font-medium text-slate-900">{link.label}</p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>
            </div>

            <Card>
              <CardContent className="pt-6">
                <h3 className="font-semibold text-slate-900">Tags</h3>
                <div className="mt-3 flex flex-wrap gap-2">
                  {TAGS.map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

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

        <footer className="mt-10 flex flex-col gap-3 border-t pt-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Chair of Computer Science II, Julius-Maximilians-Universität Würzburg</p>
          <div className="flex gap-4">
            <Link to="/about" className="hover:text-slate-900">
              About
            </Link>
            <Link to="/browse" className="hover:text-slate-900">
              Browse
            </Link>
          </div>
        </footer>
      </div>
    </div>
  );
}

import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button.tsx';

export function HomeHero() {
  return (
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
  );
}

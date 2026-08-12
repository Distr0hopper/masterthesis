import { Link } from 'react-router-dom';
import { GitMerge, LayoutGrid, Upload, Workflow } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';

const FIND_CONTENT_LINKS = [
  { label: 'Browse Components', to: '/browse', icon: LayoutGrid },
  { label: 'Browse Workflows', to: '/builder', icon: Workflow },
  { label: 'Upload a Component', to: '/upload', icon: Upload },
  { label: 'Build a Workflow', to: '/builder', icon: GitMerge },
];

export function FindContent() {
  return (
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
  );
}

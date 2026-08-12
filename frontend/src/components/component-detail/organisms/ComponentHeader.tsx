import { Link } from 'react-router-dom';
import { ChevronLeft, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import type { ComponentDetailDisplayModel } from '@/api/components';

interface ComponentHeaderProps {
  model: ComponentDetailDisplayModel;
}

export function ComponentHeader({ model }: ComponentHeaderProps) {
  return (
    <>
      <Link to="/browse" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ChevronLeft className="h-4 w-4" /> Back to Browse
      </Link>

      <Card className="mt-4">
        <CardContent className="flex flex-col gap-3 pt-6">
          <Badge variant="outline" className="w-fit">
            {model.domainDisplay}
          </Badge>

          <h1 className="font-mono text-2xl font-bold text-slate-900">{model.name}</h1>

          {model.description && <p className="text-slate-600">{model.description}</p>}

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3 text-sm text-slate-500">
            <span>{model.authorDisplay}</span>
            <span>Created {model.createdAtDisplay}</span>
            <span>Updated {model.updatedAtDisplay}</span>
            {model.repoUrl && (
              <a
                href={model.repoUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-jmu-blue-800 hover:underline"
              >
                <ExternalLink className="h-4 w-4" /> GitHub
              </a>
            )}
            {model.repoCommitShaShort && (
              <Badge variant="secondary" className="font-mono">
                {model.repoCommitShaShort}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

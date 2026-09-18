import { Link } from 'react-router-dom';
import { ChevronLeft, Download, ExternalLink, Globe, GlobeLock } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { Badge } from '@/components/ui/badge.tsx';
import { Button } from '@/components/ui/button.tsx';
import { toast } from 'sonner';
import {
  ComponentStatus,
  componentsService,
  getDomainBadgeStyle,
  useDomains,
  usePublishComponent,
  useUnpublishComponent,
  type ComponentDetailDisplayModel,
} from '@/api/components';
import { FavoriteButton } from '@/components/FavoriteButton';
import {
  canFavorite,
  canPublish as hasPublishLink,
  canUnpublish as hasUnpublishLink,
  getLink,
} from '@/api/permissions';
import { getErrorMessage } from '@/lib/errors';
import { ROUTES } from '@/lib/routes';

interface ComponentHeaderProps {
  model: ComponentDetailDisplayModel;
}

export function ComponentHeader({ model }: ComponentHeaderProps) {
  const { data: domains } = useDomains();
  const { mutate: publishComponent, isPending: isPublishing } = usePublishComponent();
  const { mutate: unpublishComponent, isPending: isUnpublishing } = useUnpublishComponent();
  const domainBadgeStyle = domains ? getDomainBadgeStyle(model.domain, domains) : undefined;

  const canPublish = hasPublishLink(model._links) && model.status === ComponentStatus.DRAFT;
  const canUnpublish = hasUnpublishLink(model._links) && model.status === ComponentStatus.PUBLISHED;

  const handlePublish = () => {
    publishComponent(getLink(model._links, 'publish')!, {
      onSuccess: () => toast.success('Component published'),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  const handleUnpublish = () => {
    unpublishComponent(getLink(model._links, 'unpublish')!, {
      onSuccess: () => toast.success('Component unpublished'),
      onError: (error) => toast.error(getErrorMessage(error)),
    });
  };

  return (
    <>
      <Link to={ROUTES.browse} className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-900">
        <ChevronLeft className="h-4 w-4" /> Back to Browse
      </Link>

      {model.status === ComponentStatus.DRAFT && (
        <div className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This component is a draft and is only visible to you. Publish it to make it public and available in
          the Workflow Builder.
        </div>
      )}

      <Card className="mt-4">
        <CardContent className="flex flex-col gap-3 pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="w-fit" style={domainBadgeStyle}>
                {model.domainDisplay}
              </Badge>

              {canFavorite(model._links) && <FavoriteButton links={model._links!} isFavorite={model.isFavorite} />}
            </div>

            <div className="flex items-center gap-2">
              <Button asChild variant="outline" size="sm">
                <a href={componentsService.getBundleUrl(model.id)}>
                  <Download className="mr-1 h-4 w-4" /> Download
                </a>
              </Button>

              {canPublish && (
                <Button
                  size="sm"
                  className="bg-jmu-blue-800 hover:bg-jmu-blue-800/90"
                  onClick={handlePublish}
                  disabled={isPublishing}
                >
                  <Globe className="mr-1 h-4 w-4" /> Publish
                </Button>
              )}

              {canUnpublish && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleUnpublish}
                  disabled={isUnpublishing}
                  title="Hide this component from the public list and the Workflow Builder again"
                >
                  <GlobeLock className="mr-1 h-4 w-4" /> Unpublish
                </Button>
              )}
            </div>
          </div>

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

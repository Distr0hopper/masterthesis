import { Link } from 'react-router-dom';
import { Card, CardContent } from '@/components/ui/card.tsx';
import { VersionStatusBadges } from '@/components/common/VersionStatusBadges';
import { latestPublished, newestFirst, useComponentVersions, type ComponentKind } from '@/api/components';
import { componentDetailRoute } from '@/lib/routes';
import { cn } from '@/lib/utils';

interface ComponentVersionsProps {
  componentId: string;
  kind: ComponentKind;
}

/**
 * Every version of the lineage the viewer may see, newest first - where the others are,
 * and which one is current. Hidden while there is only the one being viewed.
 */
export function ComponentVersions({ componentId, kind }: ComponentVersionsProps) {
  const { data: versions } = useComponentVersions(componentId);
  if (!versions || versions.length < 2) return null;

  const latest = latestPublished(versions);

  return (
    <Card className="mt-6">
      <CardContent className="pt-6">
        <h3 className="font-semibold text-slate-900">Versions</h3>

        <ul className="mt-3 flex flex-col divide-y divide-slate-100">
          {newestFirst(versions).map((v) => {
            const isViewed = v.id === componentId;
            return (
              <li
                key={v.id}
                aria-current={isViewed ? 'page' : undefined}
                className={cn('flex flex-wrap items-center gap-2 px-2 py-2', isViewed && 'rounded-md bg-slate-50')}
              >
                {isViewed ? (
                  <span className="font-mono text-sm font-semibold text-slate-900">v{v.version}</span>
                ) : (
                  <Link
                    to={componentDetailRoute(kind, v.id)}
                    className="font-mono text-sm font-semibold text-slate-900 hover:text-jmu-blue-800 hover:underline"
                  >
                    v{v.version}
                  </Link>
                )}

                <VersionStatusBadges version={v} isLatest={v.id === latest?.id} />
                {v.deprecationNote && (
                  <span className="min-w-0 truncate text-xs text-slate-500" title={v.deprecationNote}>
                    {v.deprecationNote}
                  </span>
                )}

                <span className="ml-auto text-xs text-slate-500">{v.createdAtDisplay}</span>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

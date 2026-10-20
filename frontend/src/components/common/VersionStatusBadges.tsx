import { Badge } from '@/components/ui/badge.tsx';
import { ComponentStatus, type ComponentDisplayModelBase } from '@/api/components';

interface VersionStatusBadgesProps {
  version: Pick<ComponentDisplayModelBase, 'status' | 'statusDisplay' | 'statusHint'>;
  /** the version the catalogue lists */
  isLatest: boolean;
}

/** Where one version of a lineage stands - the same badges in every list of versions. */
export function VersionStatusBadges({ version, isLatest }: VersionStatusBadgesProps) {
  return (
    <>
      {isLatest && (
        <Badge variant="secondary" title="The version listed in the catalogue and offered in the Workflow Builder">
          Latest
        </Badge>
      )}
      {version.status === ComponentStatus.DRAFT && (
        // "Draft", or "Unpublished" for one taken back - see isTakenBack
        <Badge
          variant="outline"
          className="border-amber-300 text-amber-700"
          title={version.statusHint ?? 'Only visible to you'}
        >
          {version.statusDisplay}
        </Badge>
      )}
      {version.status === ComponentStatus.DEPRECATED && (
        <Badge variant="outline" className="border-slate-400 text-slate-700">
          {version.statusDisplay}
        </Badge>
      )}
    </>
  );
}

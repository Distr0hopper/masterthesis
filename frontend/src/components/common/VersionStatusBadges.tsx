import { Badge } from '@/components/ui/badge.tsx';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ComponentStatus, type ComponentDisplayModelBase } from '@/api/components';

interface VersionStatusBadgesProps {
  version: Pick<ComponentDisplayModelBase, 'status'>;
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
      {/* "Latest" says it's the published one - a status badge only for the others */}
      {version.status !== ComponentStatus.PUBLISHED && (
        <StatusBadge status={version.status} />
      )}
    </>
  );
}

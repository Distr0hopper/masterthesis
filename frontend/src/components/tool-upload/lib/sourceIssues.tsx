import type { ReactNode } from 'react';
import { ComponentLink } from '@/components/common/ComponentLink';
import { ComponentStatus } from '@/api/components';
import type { PackagePreviewDto } from '@/api/tools';

/** Why a fetched repo can't be packaged at all - shown on the source step, blocks continuing. */
export function sourceIssuesOf(preview: PackagePreviewDto | undefined): ReactNode[] {
  const existing = preview?.existing;
  if (!preview || !existing) return [];
  // the tool the repo is already packaged as - where to go instead
  const existingLink = (
    <ComponentLink
      componentId={existing.id}
      kind={existing.kind}
      name={existing.name}
      version={existing.version}
      className="inline-flex"
    />
  );
  if (preview.alreadyPackaged) {
    return [
      <>
        Already up to date - commit <code className="text-xs">{preview.commitSha.slice(0, 7)}</code> is already packaged
        as {existingLink}
        {existing.status === ComponentStatus.DRAFT ? ', which is still a draft - publish it from its page.' : '.'}
      </>,
    ];
  }
  if (!existing.canAddVersion) {
    return [<>This repository is already packaged as {existingLink}, and only its owner can add new versions.</>];
  }
  return [];
}

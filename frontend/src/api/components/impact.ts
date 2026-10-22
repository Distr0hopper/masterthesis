import { ComponentStatus, type ComponentAncestorDto, type ComponentImpactDto } from './types';

/** The caller's own public workflows above a version that are deprecated - they block a retract. */
export function ownDeprecatedAncestors(impact: ComponentImpactDto): ComponentAncestorDto[] {
  return impact.ownPublicAncestors.filter((ancestor) => ancestor.status === ComponentStatus.DEPRECATED);
}

/** The caller's own published workflows above a version still within their unpublish window - they become drafts along with it. */
export function ownPublishedAncestors(impact: ComponentImpactDto): ComponentAncestorDto[] {
  return impact.ownPublicAncestors.filter(
    (ancestor) => ancestor.status !== ComponentStatus.DEPRECATED && ancestor.unpublishable,
  );
}

/** The caller's own published workflows above a version past their unpublish window - they block a retract. */
export function ownLockedAncestors(impact: ComponentImpactDto): ComponentAncestorDto[] {
  return impact.ownPublicAncestors.filter(
    (ancestor) => ancestor.status !== ComponentStatus.DEPRECATED && !ancestor.unpublishable,
  );
}

/**
 * Whether unpublishing or deleting the version is impossible: another user's public workflow
 * runs it (theirs would break), or one of your own deprecated ones does (a deprecated version
 * never goes straight back to draft), or one of your own published past its unpublish window
 * (it can't become a draft anymore). Mirrors the backend's retract_impact.
 */
export function isRetractBlocked(impact: ComponentImpactDto | undefined): boolean {
  return (
    !!impact &&
    (impact.foreignPublicAncestors.length > 0 ||
      ownDeprecatedAncestors(impact).length > 0 ||
      ownLockedAncestors(impact).length > 0)
  );
}

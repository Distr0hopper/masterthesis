import { ComponentStatus, type ComponentAncestorDto, type ComponentImpactDto } from './types';

/** The caller's own public workflows above a version that are deprecated - they block a retract. */
export function ownDeprecatedAncestors(impact: ComponentImpactDto): ComponentAncestorDto[] {
  return impact.ownPublicAncestors.filter((ancestor) => ancestor.status === ComponentStatus.DEPRECATED);
}

/** The caller's own published workflows above a version - they become drafts along with it. */
export function ownPublishedAncestors(impact: ComponentImpactDto): ComponentAncestorDto[] {
  return impact.ownPublicAncestors.filter((ancestor) => ancestor.status !== ComponentStatus.DEPRECATED);
}

/**
 * Whether unpublishing or deleting the version is impossible: another user's public workflow
 * runs it (theirs would break), or one of your own deprecated ones does (a deprecated version
 * never goes straight back to draft). Mirrors the backend's retract_impact.
 */
export function isRetractBlocked(impact: ComponentImpactDto | undefined): boolean {
  return !!impact && (impact.foreignPublicAncestors.length > 0 || ownDeprecatedAncestors(impact).length > 0);
}

import { describe, expect, it } from 'vitest';
import { ComponentStatus, type ComponentAncestorDto, type ComponentImpactDto } from './types';
import { isRetractBlocked, ownLockedAncestors, ownPublishedAncestors } from './impact';

function ancestor(name: string, status: ComponentStatus, unpublishable: boolean): ComponentAncestorDto {
  return { id: name, name, version: 1, status, createdBy: null, unpublishable };
}

function impact(own: ComponentAncestorDto[]): ComponentImpactDto {
  return {
    ownPublicAncestors: own,
    foreignPublicAncestors: [],
    workflows: [],
    hiddenWorkflowCount: 0,
    drafts: [],
    otherDraftCount: 0,
  };
}

describe('the own public workflows above a version being unpublished', () => {
  const fresh = ancestor('fresh', ComponentStatus.PUBLISHED, true);
  const old = ancestor('old', ComponentStatus.PUBLISHED, false);

  it('takes those still within their window along as drafts', () => {
    expect(ownPublishedAncestors(impact([fresh, old]))).toEqual([fresh]);
    expect(isRetractBlocked(impact([fresh]))).toBe(false);
  });

  it('is blocked by one past its window - it can never become a draft again', () => {
    expect(ownLockedAncestors(impact([fresh, old]))).toEqual([old]);
    expect(isRetractBlocked(impact([fresh, old]))).toBe(true);
  });

  it('is blocked by a deprecated one, as before', () => {
    expect(isRetractBlocked(impact([ancestor('dep', ComponentStatus.DEPRECATED, false)]))).toBe(true);
  });
});

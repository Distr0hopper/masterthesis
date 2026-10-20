import { describe, expect, it } from 'vitest';
import { ComponentStatus, type ComponentListItemBaseDto } from './types';
import { TAKEN_BACK_HINT, TAKEN_BACK_LABEL, toDisplayModelBase } from './transformer';

function dto(status: ComponentStatus, firstPublishedAt: string | null): ComponentListItemBaseDto {
  return {
    kind: 'workflow',
    id: 'wf-1',
    name: 'SpatialClustering',
    description: null,
    authorName: null,
    createdBy: null,
    version: 1,
    domains: [],
    status,
    deprecationNote: null,
    firstPublishedAt,
    createdAt: '2026-09-21T09:25:28Z',
    isFavorite: false,
    parameters: null,
  };
}

const PUBLISHED_ON = '2026-09-22T10:00:00Z';

describe('toDisplayModelBase - a draft taken back after it was public', () => {
  it('reads as unpublished, and says what that means', () => {
    const model = toDisplayModelBase(dto(ComponentStatus.DRAFT, PUBLISHED_ON));
    expect(model).toMatchObject({ isTakenBack: true, statusDisplay: TAKEN_BACK_LABEL, statusHint: TAKEN_BACK_HINT });
  });

  it('is not the same as a draft never published - that one is still being worked on', () => {
    const model = toDisplayModelBase(dto(ComponentStatus.DRAFT, null));
    expect(model).toMatchObject({ isTakenBack: false, statusDisplay: 'Draft', statusHint: null });
  });

  it.each([ComponentStatus.PUBLISHED, ComponentStatus.DEPRECATED])('nor is a public version (%s)', (status) => {
    const model = toDisplayModelBase(dto(status, PUBLISHED_ON));
    expect(model.isTakenBack).toBe(false);
    expect(model.statusHint).toBeNull();
  });
});

describe('toDisplayModelBase - how many versions a list row stands for', () => {
  it('carries the count where the response has one (own lists), and null elsewhere', () => {
    expect(toDisplayModelBase({ ...dto(ComponentStatus.DRAFT, null), versionCount: 3 }).versionCount).toBe(3);
    expect(toDisplayModelBase(dto(ComponentStatus.PUBLISHED, PUBLISHED_ON)).versionCount).toBeNull();
  });
});

import { describe, expect, it } from 'vitest';
import { ComponentStatus, type ComponentDetailBaseDto, type ComponentListItemBaseDto } from './types';
import { toDetailFields, toDisplayModelBase } from './transformer';

function dto(status: ComponentStatus): ComponentListItemBaseDto {
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
    firstPublishedAt: null,
    createdAt: '2026-09-21T09:25:28Z',
    isFavorite: false,
    parameters: null,
  };
}

function detailDto(unpublishableUntil: string | null): ComponentDetailBaseDto {
  return {
    ...dto(ComponentStatus.PUBLISHED),
    repoUrl: null,
    repoCommitSha: null,
    doi: null,
    cwlContent: 'class: Workflow',
    ontologyUrl: null,
    source: 'manual_upload',
    parameters: [],
    updatedAt: '2026-09-21T09:25:28Z',
    unpublishableUntil,
  };
}

describe('toDisplayModelBase', () => {
  it.each([ComponentStatus.DRAFT, ComponentStatus.PUBLISHED, ComponentStatus.DEPRECATED])(
    'shows the plain status (%s)',
    (status) => {
      expect(toDisplayModelBase(dto(status)).statusDisplay).toBe(
        { draft: 'Draft', published: 'Published', deprecated: 'Deprecated' }[status],
      );
    },
  );

  it('carries how many versions a list row stands for where the response has one (own lists), and null elsewhere', () => {
    expect(toDisplayModelBase({ ...dto(ComponentStatus.DRAFT), versionCount: 3 }).versionCount).toBe(3);
    expect(toDisplayModelBase(dto(ComponentStatus.PUBLISHED)).versionCount).toBeNull();
  });
});

describe('toDetailFields - the unpublish window', () => {
  it('says until when an accidental publish can still be taken back', () => {
    const until = '2026-10-22T10:00:00Z';
    const display = toDetailFields(detailDto(until)).unpublishableUntilDisplay;
    expect(display).not.toBeNull();
    expect(display).toContain('2026');
  });

  it('says nothing once the window has closed', () => {
    expect(toDetailFields(detailDto(null)).unpublishableUntilDisplay).toBeNull();
  });
});

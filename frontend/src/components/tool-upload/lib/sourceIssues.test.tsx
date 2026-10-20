import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { ComponentStatus, type ExistingComponentDto } from '@/api/components';
import type { PackagePreviewDto } from '@/api/tools';
import { sourceIssuesOf } from './sourceIssues';

function existing(overrides: Partial<ExistingComponentDto> = {}): ExistingComponentDto {
  return {
    id: 'tool-1',
    kind: 'tool',
    name: 'RemoveOutliers',
    version: 2,
    domains: ['animal_behavior'],
    status: ComponentStatus.PUBLISHED,
    createdAt: '2026-10-19T10:29:02Z',
    canAddVersion: true,
    ...overrides,
  };
}

function preview(overrides: Partial<PackagePreviewDto> = {}): PackagePreviewDto {
  return {
    description: null,
    cwlContent: 'class: CommandLineTool',
    cwlType: 'CommandLineTool',
    dockerfileContent: null,
    dockerPullReference: null,
    ontologyUrl: null,
    parameters: [],
    repoName: 'RemoveOutliers',
    repoUrl: 'https://github.com/Distr0hopper/RemoveOutliers',
    commitSha: '023fdf3bd6b5b753259e0cb68d84c0cc78c632cf',
    author: null,
    existing: null,
    alreadyPackaged: false,
    ...overrides,
  };
}

/** each issue as rendered markup - text and the link it carries */
function rendered(issues: ReturnType<typeof sourceIssuesOf>): string[] {
  return issues.map((issue) => renderToStaticMarkup(<MemoryRouter>{issue}</MemoryRouter>));
}

/** the rendered text with tags stripped - what the user reads. ComponentLink keeps name and
 * version together with a non-breaking space, compared here as a plain one */
function textOf(markup: string): string {
  return markup.replace(/<[^>]+>/g, '').replace(/&nbsp;|\u00a0/g, ' ');
}

describe('sourceIssuesOf - why a fetched repo cannot be packaged', () => {
  it('has nothing to say before a fetch, or about a repo never packaged', () => {
    expect(sourceIssuesOf(undefined)).toEqual([]);
    expect(sourceIssuesOf(preview())).toEqual([]);
  });

  it('lets the owner package a new commit as the next version', () => {
    expect(sourceIssuesOf(preview({ existing: existing() }))).toEqual([]);
  });

  it('stops at an unchanged repo and links the tool already holding that commit', () => {
    const [issue] = rendered(sourceIssuesOf(preview({ existing: existing(), alreadyPackaged: true })));

    expect(textOf(issue)).toContain('Already up to date - commit 023fdf3 is already packaged as RemoveOutliers v2.');
    expect(issue).toContain('href="/tools/tool-1"');
  });

  it('points to publishing when that tool is still a draft', () => {
    const [issue] = rendered(
      sourceIssuesOf(preview({ existing: existing({ status: ComponentStatus.DRAFT }), alreadyPackaged: true })),
    );
    expect(textOf(issue)).toContain('which is still a draft - publish it from its page.');
  });

  it("names whose tool it is when it isn't yours to version", () => {
    const [issue] = rendered(sourceIssuesOf(preview({ existing: existing({ canAddVersion: false }) })));

    expect(textOf(issue)).toContain('already packaged as RemoveOutliers v2, and only its owner can add new versions.');
    expect(issue).toContain('href="/tools/tool-1"');
  });
});

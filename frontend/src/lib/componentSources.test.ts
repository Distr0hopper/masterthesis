import { describe, expect, it } from 'vitest';
import { ComponentSource } from '@/api/components/types';
import { parseSource, sourcesFor } from './componentSources';

describe('the sources My Components offers to filter by', () => {
  it('are all of them while no kind is chosen', () => {
    expect(sourcesFor(undefined)).toEqual([
      ComponentSource.AUTOMATED_PACKAGING,
      ComponentSource.WORKFLOW_BUILDER,
      ComponentSource.MANUAL_UPLOAD,
    ]);
  });

  it('are only the ones a kind can come from', () => {
    expect(sourcesFor('tool')).toEqual([ComponentSource.AUTOMATED_PACKAGING, ComponentSource.MANUAL_UPLOAD]);
    expect(sourcesFor('workflow')).toEqual([ComponentSource.WORKFLOW_BUILDER, ComponentSource.MANUAL_UPLOAD]);
  });

  it('ignores anything in the URL that is no source', () => {
    expect(parseSource('automated_packaging')).toBe(ComponentSource.AUTOMATED_PACKAGING);
    expect(parseSource('github')).toBeUndefined();
    expect(parseSource(null)).toBeUndefined();
  });
});

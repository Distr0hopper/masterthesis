import { describe, expect, it } from 'vitest';
import { ComponentStatus } from '@/api/components';
import { saveTarget } from './saveTarget';

const linked = (version: number, status: ComponentStatus) => ({ id: 'w', version, status });

describe('what Save says it will do', () => {
  it('is a plain Save while nothing or a draft is in My Components - it is overwritten in place', () => {
    expect(saveTarget(null).label).toBe('Save');
    expect(saveTarget(linked(2, ComponentStatus.DRAFT))).toEqual({
      label: 'Save',
      hint: 'Saves the canvas and updates the draft v2 in My Components',
    });
  });

  it.each([ComponentStatus.PUBLISHED, ComponentStatus.DEPRECATED])(
    'names the next version once the newest is %s - that one never changes',
    (status) => {
      const target = saveTarget(linked(2, status));
      expect(target.label).toBe('Save as v3');
      expect(target.hint).toMatch(/^v2 stays (published|deprecated) - v3 is a draft/);
    },
  );
});

import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { ComponentLink } from '@/components/common/ComponentLink';

/** the rendered text with tags stripped - i.e. what copy-paste and screen readers get */
function textOf(markup: string): string {
  return markup.replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ');
}

describe('ComponentLink text content', () => {
  it('separates name and version with a real character, not a CSS gap', () => {
    const html = renderToStaticMarkup(
      <MemoryRouter>
        <ComponentLink componentId="abc" name="Remove Outliers" version={1} />
      </MemoryRouter>,
    );
    expect(textOf(html)).toBe('Remove Outliers v1');
    expect(textOf(html)).not.toContain('Outliersv1');
  });
});

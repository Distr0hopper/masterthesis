import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { publishedTool, signUp } from './support.ts';

// room for the palette, the canvas with two nodes side by side, and the inspector
test.use({ viewport: { width: 1680, height: 1000 } });

/** drags a palette card onto the canvas at (x, y) - the builder's HTML5 drag and drop */
async function dropOnCanvas(page: Page, name: string, x: number, y: number) {
  await page.getByPlaceholder('Search by name...').fill(name);
  const card = page.locator('[draggable="true"]').filter({ hasText: name }).first();
  await card.dragTo(page.locator('.react-flow__pane'), { targetPosition: { x, y } });
  await expect(page.locator('.react-flow__node').filter({ hasText: name })).toBeVisible();
}

/** waits out the canvas's pan/zoom animation - handles measured mid-way are already elsewhere */
async function settled(page: Page) {
  const viewport = page.locator('.react-flow__viewport');
  let previous = '';
  await expect
    .poll(async () => {
      const current = (await viewport.getAttribute('style')) ?? '';
      const still = current === previous;
      previous = current;
      return still;
    }, { intervals: [150] })
    .toBe(true);
}

/** wires `output` of one node to `input` of another, by mouse - as a user draws an edge */
async function connect(page: Page, from: string, output: string, to: string, input: string) {
  await settled(page);
  const source = page.locator('.react-flow__node').filter({ hasText: from }).locator(`.react-flow__handle[data-handleid="${output}"]`);
  const target = page.locator('.react-flow__node').filter({ hasText: to }).locator(`.react-flow__handle[data-handleid="${input}"]`);
  const a = (await source.boundingBox())!;
  const b = (await target.boundingBox())!;
  await page.mouse.move(a.x + a.width / 2, a.y + a.height / 2);
  await page.mouse.down();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: 10 });
  await page.mouse.up();
}

test('a workflow drawn on the canvas is saved as a draft and exported as a runnable archive', async ({ page }) => {
  await signUp(page);
  const stamp = Date.now();
  const reader = await publishedTool(page, `read-tracks-${stamp}`);
  const cleaner = await publishedTool(page, `clean-tracks-${stamp}`);

  await page.goto('/builder/new');
  await dropOnCanvas(page, reader.name, 60, 150);
  // the canvas zooms in on the first node - zoom back out, so the second lands beside it, not on it
  for (let i = 0; i < 3; i++) await page.getByRole('button', { name: /zoom out/i }).click();
  await settled(page);
  await dropOnCanvas(page, cleaner.name, 700, 150);
  await connect(page, reader.name, 'cleaned', cleaner.name, 'tracks');
  await expect(page.locator('.react-flow__edge')).toHaveCount(1);

  await page.getByLabel('Workflow name').fill(`Track pipeline ${stamp}`);
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page).toHaveURL(/\/builder\/[0-9a-f-]{36}$/);
  // saved as v1 of a draft workflow in My Components - and the top bar says so
  await expect(page.getByText('Saved - v1 in My Components is up to date.')).toBeVisible();
  await expect(page.getByText('Saved just now')).toBeVisible();

  // the canvas comes back as it was drawn
  await page.reload();
  await expect(page.locator('.react-flow__node')).toHaveCount(2);
  await expect(page.locator('.react-flow__edge')).toHaveCount(1);
  await expect(page.getByLabel('Workflow name')).toHaveValue(`Track pipeline ${stamp}`);

  // exported: one archive with the pipeline and both step documents
  await page.getByRole('button', { name: 'Export' }).click();
  await page.getByRole('menuitem').first().click();
  // the reader's own input is fed by nothing - allowed, it becomes the workflow's input, but said
  const warning = page.getByRole('alertdialog');
  await expect(warning).toContainText(`"${reader.name}" input "tracks" is not connected`);
  const downloading = page.waitForEvent('download');
  await warning.getByRole('button', { name: 'Export anyway' }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toMatch(/\.zip$/);
  // a zip's central directory lists its file names uncompressed
  const archive = (await readFile((await download.path())!)).toString('latin1');
  expect(archive).toContain(`${reader.name}.cwl`);
  expect(archive).toContain(`${cleaner.name}.cwl`);

  // and it is in My Components, as a draft only its creator sees
  await page.goto('/my-components');
  await expect(page.getByText(`Track pipeline ${stamp}`).first()).toBeVisible();
});

test('an unnamed canvas is not exported', async ({ page }) => {
  await signUp(page);
  const tool = await publishedTool(page, `lonely-${Date.now()}`);

  await page.goto('/builder/new');
  await dropOnCanvas(page, tool.name, 300, 200);
  await page.getByRole('button', { name: 'Export' }).click();
  await page.getByRole('menuitem').first().click();

  // a blocking error, not a warning - there is no way past it but naming the workflow
  const dialog = page.getByRole('alertdialog');
  await expect(dialog).toContainText(/name/i);
  await expect(dialog.getByRole('button', { name: 'Export anyway' })).toHaveCount(0);
});

test('a saved workflow runs as a nested step on another canvas - but never on its own', async ({ page }) => {
  await signUp(page);
  const stamp = Date.now();
  const tool = await publishedTool(page, `inner-tool-${stamp}`);
  const innerName = `Inner pipeline ${stamp}`;

  await page.goto('/builder/new');
  await dropOnCanvas(page, tool.name, 300, 200);
  await page.getByLabel('Workflow name').fill(innerName);
  await page.getByRole('button', { name: 'Save', exact: true }).click();
  await expect(page.getByText('Saved - v1 in My Components is up to date.')).toBeVisible();

  // its own palette leaves it out - a workflow cannot contain itself
  await page.getByPlaceholder('Search by name...').fill(innerName);
  await expect(page.getByText('No components match these filters.')).toBeVisible();

  // another canvas offers it - narrowed to workflows, the tool is gone from the palette
  await page.goto('/builder/new');
  const palette = page.locator('aside');
  await palette.getByRole('tab', { name: 'Workflows' }).click();
  await page.getByPlaceholder('Search by name...').fill(tool.name);
  await expect(page.getByText('No components match these filters.')).toBeVisible();
  await palette.getByRole('tab', { name: 'All' }).click();

  // and it lands as a nested workflow node
  await dropOnCanvas(page, innerName, 300, 200);
  await expect(
    page.locator('.react-flow__node').filter({ hasText: innerName }).getByLabel('Nested workflow'),
  ).toBeVisible();
});

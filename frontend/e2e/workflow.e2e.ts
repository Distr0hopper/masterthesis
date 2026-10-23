import { expect, test } from '@playwright/test';
import { signUp } from './support.ts';

/** a self-contained workflow: its one step's tool is written inline, not in a file of its own */
const PIPELINE = (toolStep: string) => `cwlVersion: v1.2
class: Workflow
label: Track cleaning
inputs:
  tracks: File
outputs:
  result:
    type: File
    outputSource: ${toolStep}/cleaned
steps:
  ${toolStep}:
    run:
      class: CommandLineTool
      doc: Drops fixes faster than a bird can fly
      baseCommand: [Rscript, clean.R]
      inputs:
        tracks: File
      outputs:
        cleaned:
          type: File
          outputBinding: {glob: out.rds}
    in: {tracks: tracks}
    out: [cleaned]
`;

test('an uploaded workflow brings its new tool along and publishes it with it', async ({ page, browser }) => {
  await signUp(page);
  const stamp = Date.now();
  const toolStep = `clean_tracks_${stamp}`;

  await page.goto('/workflows/upload');
  await page
    .locator('input[type="file"]')
    .setInputFiles({ name: 'pipeline.cwl', mimeType: 'application/octet-stream', buffer: Buffer.from(PIPELINE(toolStep)) });

  // read as soon as it is chosen: the inline tool is offered as a new component, named after its step
  await expect(page.getByLabel('Name', { exact: true })).toHaveValue(`clean-tracks-${stamp}`);
  await page.getByLabel('Workflow Name').fill(`track-cleaning-${stamp}`);
  // three domain pickers: the workflow's, one for all new components at once, the tool's own
  const animalBehavior = page.getByLabel('Animal Behavior');
  await expect(animalBehavior).toHaveCount(3);
  await animalBehavior.nth(0).check();
  await animalBehavior.nth(1).check();
  await expect(animalBehavior.nth(2)).toBeChecked();
  await page.getByRole('button', { name: 'Save Workflow' }).click();

  // a draft workflow running a draft tool
  await expect(page).toHaveURL(/\/workflows\/[0-9a-f-]{36}$/);
  const workflowUrl = page.url();
  await expect(page.getByText(/is a draft and is only visible to you/)).toBeVisible();

  // publishing it names the draft tool going public along with it
  await page.getByRole('button', { name: 'Publish' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('1 component(s) will also be published');
  await dialog.getByRole('button', { name: /^Publish/ }).click();
  await expect(dialog).toBeHidden();

  const visitor = await browser.newPage();
  await visitor.goto(workflowUrl);
  await expect(visitor.getByRole('heading', { name: `track-cleaning-${stamp}` })).toBeVisible();
  await visitor.goto('/browse?kind=tool');
  await expect(visitor.getByText(`clean-tracks-${stamp}`).first()).toBeVisible();
  await visitor.close();
});

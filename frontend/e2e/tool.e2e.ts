import { expect, test } from '@playwright/test';
import { signUp, TOOL_CWL } from './support.ts';

test('a tool uploaded through the wizard stays private until it is published', async ({ page, browser }) => {
  await signUp(page);
  const name = `clean-tracks-${Date.now()}`;

  // step 1: the file - read as soon as it is chosen, then on to step 2
  await page.goto('/tools/upload');
  await page
    .locator('input[type="file"]')
    .setInputFiles({ name: 'clean-tracks.cwl', mimeType: 'application/octet-stream', buffer: Buffer.from(TOOL_CWL()) });

  // step 2: review what was read from it, and name it - prefilled from the file name
  await expect(page.getByLabel('Tool Name')).toHaveValue('clean-tracks');
  await expect(page.getByText('tracks', { exact: true }).first()).toBeVisible();
  await expect(page.getByText('max_speed').first()).toBeVisible();
  await page.getByLabel('Tool Name').fill(name);
  await page.getByLabel('Animal Behavior').check();
  await page.getByRole('button', { name: 'Create Tool' }).click();

  // a draft, on its own page
  await expect(page).toHaveURL(/\/tools\/[0-9a-f-]{36}$/);
  const toolUrl = page.url();
  await expect(page.getByRole('heading', { name })).toBeVisible();
  await expect(page.getByText(/is a draft and is only visible to you/)).toBeVisible();

  // nobody else can open it - not even knowing its address
  const stranger = await browser.newPage();
  await stranger.goto(toolUrl);
  await expect(stranger.getByText(/not found/i).first()).toBeVisible();
  await stranger.goto(`/browse?search=${name}`);
  await expect(stranger.getByText(name)).toHaveCount(0);

  // published, it is public
  await page.getByRole('button', { name: 'Publish' }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('will become visible to everyone');
  await dialog.getByRole('button', { name: /^Publish/ }).click();
  await expect(dialog).toBeHidden();
  await expect(page.getByText(/is a draft and is only visible to you/)).toHaveCount(0);

  await stranger.goto(toolUrl);
  await expect(stranger.getByRole('heading', { name })).toBeVisible();
  await stranger.goto(`/browse?search=${name}`);
  await expect(stranger.getByText(name).first()).toBeVisible();
  await stranger.close();
});

test('an upload with a name already taken is stopped before it is sent', async ({ page }) => {
  await signUp(page);
  const name = `taken-${Date.now()}`;
  const upload = async () => {
    await page.goto('/tools/upload');
    await page
      .locator('input[type="file"]')
      .setInputFiles({ name: 'tool.cwl', mimeType: 'application/octet-stream', buffer: Buffer.from(TOOL_CWL()) });
    await page.getByLabel('Tool Name').fill(name);
    await page.getByLabel('Animal Behavior').check();
  };

  await upload();
  await page.getByRole('button', { name: 'Create Tool' }).click();
  await expect(page).toHaveURL(/\/tools\/[0-9a-f-]{36}$/);

  await upload();
  await expect(page.getByText(/already taken|add a new version/i).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create Tool' })).toBeDisabled();
});

test('a file that is not CWL is refused on the first step', async ({ page }) => {
  await signUp(page);
  await page.goto('/tools/upload');
  await page
    .locator('input[type="file"]')
    .setInputFiles({ name: 'notes.cwl', mimeType: 'application/octet-stream', buffer: Buffer.from('class: [broken') });
  await page.getByRole('button', { name: 'Continue' }).click();

  await expect(page.getByText(/invalid|could not|yaml/i).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Create Tool' })).toHaveCount(0);
});

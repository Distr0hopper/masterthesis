import { expect, test } from '@playwright/test';
import { loginCode, requestCode, signUp, uniqueEmail } from './support.ts';

test('a new user signs in with the emailed code and completes their profile first', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Login' }).first().click();

  const user = await signUp(page);

  // signed in: the header greets them by the name they just gave - also after a reload
  await expect(page.getByRole('banner')).toContainText(user.first);
  await page.reload();
  await expect(page.getByRole('banner')).toContainText(user.first);
});

test('a wrong code is refused and the right one still works', async ({ page }) => {
  const email = uniqueEmail();
  await requestCode(page, email);
  const code = await loginCode(page.request, email);
  const wrong = String((Number(code) + 1) % 1_000_000).padStart(6, '0');

  await page.getByLabel('Login code').fill(wrong);
  await page.getByRole('button', { name: 'Verify and sign in' }).click();
  await expect(page.getByText(/invalid|incorrect|wrong/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel('Login code').fill(code);
  await page.getByRole('button', { name: 'Verify and sign in' }).click();
  await expect(page).toHaveURL(/\/profile$/);
});

test('a protected page sends a visitor to log in and back there afterwards', async ({ page }) => {
  // a returning user - their profile is complete, so nothing comes in between
  const { email } = await signUp(page);
  await page.evaluate(() => localStorage.clear());

  await page.goto('/my-components');
  await expect(page).toHaveURL(/\/login\?redirect=%2Fmy-components/);

  await requestCode(page, email);
  await page.getByLabel('Login code').fill(await loginCode(page.request, email));
  await page.getByRole('button', { name: 'Verify and sign in' }).click();

  await expect(page).toHaveURL(/\/my-components$/);
});

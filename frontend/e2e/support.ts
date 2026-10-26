import { expect, type APIRequestContext, type Page } from '@playwright/test';
import { BACKEND_URL } from '../playwright.config.ts';

const MAILHOG_API = 'http://localhost:8025/api/v2';

/** an address nobody else in this run uses - a new account on first login */
export function uniqueEmail(who = 'user'): string {
  return `e2e-${who}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}@example.com`;
}

/** the login code Mailhog received for `email` - polled, since the email is sent async */
export async function loginCode(request: APIRequestContext, email: string): Promise<string> {
  let code: string | undefined;
  await expect
    .poll(
      async () => {
        const response = await request.get(`${MAILHOG_API}/search`, { params: { kind: 'to', query: email } });
        const { items } = (await response.json()) as { items: { Created: string; Content: { Body: string } }[] };
        // only the newest code is valid - a new one replaces the earlier ones
        const newest = items.sort((a, b) => b.Created.localeCompare(a.Created))[0];
        code = newest?.Content.Body.match(/\b(\d{6})\b/)?.[1];
        return code;
      },
      { message: `no login code for ${email} in Mailhog (is make docker-infra running?)` },
    )
    .toBeTruthy();
  return code!;
}

/** asks for a code on /login and stops at the code step */
export async function requestCode(page: Page, email: string): Promise<void> {
  if (!page.url().includes('/login')) await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByRole('button', { name: 'Send login code' }).click();
  await expect(page.getByLabel('Login code')).toBeVisible();
}

/** a full first login of a new account: code from Mailhog, then the profile it asks for */
export async function signUp(page: Page, name = { first: 'Ada', last: 'Lovelace' }, email = uniqueEmail()) {
  await requestCode(page, email);
  await page.getByLabel('Login code').fill(await loginCode(page.request, email));
  await page.getByRole('button', { name: 'Verify and sign in' }).click();

  await expect(page).toHaveURL(/\/profile$/);
  await page.getByLabel('First Name').fill(name.first);
  await page.getByLabel('Last Name').fill(name.last);
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page).toHaveURL(/\/$/);
  return { email, ...name };
}

/** the signed-in user's access token, as the SPA keeps it */
export async function accessToken(page: Page): Promise<string> {
  const stored = await page.evaluate(() => localStorage.getItem('auth-storage'));
  const token = stored ? (JSON.parse(stored) as { state: { token: string | null } }).state.token : null;
  if (!token) throw new Error('not signed in');
  return token;
}

export const TOOL_CWL = (baseCommand = 'clean.R') => `cwlVersion: v1.2
class: CommandLineTool
doc: Drops fixes faster than a bird can fly
baseCommand: [Rscript, ${baseCommand}]
inputs:
  tracks:
    type: File
  max_speed:
    type: double
    default: 20
outputs:
  cleaned:
    type: File
    outputBinding: {glob: out.rds}
`;

/**
 * A published tool, made straight through the API - for tests whose subject is what comes
 * after (the builder, a workflow), not the upload wizard itself.
 */
export async function publishedTool(page: Page, name: string): Promise<{ id: string; name: string }> {
  const headers = { Authorization: `Bearer ${await accessToken(page)}` };
  const created = await page.request.post(`${BACKEND_URL}/tools`, {
    headers,
    multipart: {
      name,
      domains: 'animal_behavior',
      cwlFile: {
        name: `${name}.cwl`,
        mimeType: 'application/octet-stream',
        buffer: Buffer.from(TOOL_CWL(`${name}.R`)),
      },
    },
  });
  expect(created.status(), await created.text()).toBe(201);
  const { id } = (await created.json()) as { id: string };
  const published = await page.request.post(`${BACKEND_URL}/components/${id}/commands`, {
    headers,
    data: { command: 'PUBLISH' },
  });
  expect(published.status(), await published.text()).toBe(200);
  return { id, name };
}

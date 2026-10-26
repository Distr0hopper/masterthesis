import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import axios, {
  AxiosError,
  type Axios,
  type AxiosAdapter,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';

// what the browser would provide - the store persists to localStorage, the interceptor
// reads and sets window.location
const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => storage.set(key, value),
  removeItem: (key: string) => storage.delete(key),
});
const location = { pathname: '/components/mine', search: '?kind=tool', href: '', assign: vi.fn() };
vi.stubGlobal('window', { location });

const toast = vi.hoisted(() => ({ warning: vi.fn() }));
vi.mock('sonner', () => ({ toast }));

const { apiClient } = await import('./client');
const { useAuthStore } = await import('@/store/auth.store');

const HOUR = 60 * 60 * 1000;

/** an unsigned token issued `age` ago, valid for `lifetime` - the frontend never checks the signature */
function token(age = 0, lifetime = 24 * HOUR): string {
  const issuedAt = Date.now() - age;
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, '');
  return `${encode({ alg: 'HS256' })}.${encode({ sub: 'u', iat: issuedAt / 1000, exp: (issuedAt + lifetime) / 1000 })}.sig`;
}

/** an adapter answering every request with `status`, remembering what was sent */
function server(status = 200, data: unknown = { ok: true }, headers: Record<string, string> = {}) {
  const sent: InternalAxiosRequestConfig[] = [];
  const adapter: AxiosAdapter = async (config) => {
    sent.push(config);
    const response = { data, status, statusText: '', headers, config } as AxiosResponse;
    if (status >= 400) throw new AxiosError('failed', String(status), config, null, response);
    return response;
  };
  return { adapter, sent };
}

const realRequest = axios.Axios.prototype.request;

/** answers every request apiClient makes without a test's own adapter - getBlob takes no
 *  config, so its tests set one here; anything else fails loudly instead of reaching a
 *  real server (a dev backend may well be listening on VITE_API_BASE_URL) */
function answerWith(adapter: AxiosAdapter) {
  vi.spyOn(axios.Axios.prototype, 'request').mockImplementation(function (this: Axios, config) {
    const own = typeof (config as InternalAxiosRequestConfig).adapter === 'function';
    return realRequest.call(this, own ? config : { ...(config as object), adapter });
  } as typeof realRequest);
}

beforeEach(() => {
  answerWith(async (config) => {
    throw new Error(`unexpected network request to ${config.url}`);
  });
  useAuthStore.getState().logout();
  location.href = '';
  toast.warning.mockClear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('the request interceptor', () => {
  it('sends the token while it is valid, and nothing without one', async () => {
    const { adapter, sent } = server();
    await apiClient.get('/components', { adapter });
    expect(sent[0].headers.Authorization).toBeUndefined();

    const valid = token();
    useAuthStore.getState().setToken(valid);
    await apiClient.get('/components', { adapter });
    expect(sent[1].headers.Authorization).toBe(`Bearer ${valid}`);
  });

  it('ends an expired session once, with a message, and sends the request anonymously', async () => {
    useAuthStore.getState().setToken(token(25 * HOUR));
    const { adapter, sent } = server();

    await apiClient.get('/components', { adapter });
    await apiClient.get('/components', { adapter });

    expect(sent.map((c) => c.headers.Authorization)).toEqual([undefined, undefined]);
    expect(useAuthStore.getState().token).toBeNull();
    expect(toast.warning).toHaveBeenCalledTimes(1);
  });

  it('renews a due token in the background - once for many requests at the same time', async () => {
    const due = token(2 * HOUR);
    useAuthStore.getState().setToken(due);
    const fresh = token();
    const refresh = vi.spyOn(axios, 'post').mockResolvedValue({ data: { accessToken: fresh, expiresIn: 86400 } });
    const { adapter, sent } = server();

    await Promise.all([apiClient.get('/a', { adapter }), apiClient.get('/b', { adapter })]);
    await vi.waitFor(() => expect(useAuthStore.getState().token).toBe(fresh));

    expect(refresh).toHaveBeenCalledTimes(1);
    expect(refresh.mock.calls[0][0]).toMatch(/\/auth\/refresh$/);
    // the requests themselves went out with the token they had
    expect(sent.map((c) => c.headers.Authorization)).toEqual([`Bearer ${due}`, `Bearer ${due}`]);
  });

  it('does not renew a token during its first hour', async () => {
    useAuthStore.getState().setToken(token(10 * 60 * 1000));
    const refresh = vi.spyOn(axios, 'post');

    await apiClient.get('/a', { adapter: server().adapter });

    expect(refresh).not.toHaveBeenCalled();
  });
});

describe('the 401 interceptor', () => {
  it('logs out a rejected session and sends the user to log in, remembering where they were', async () => {
    useAuthStore.getState().setToken(token());

    await expect(apiClient.get('/components/mine', { adapter: server(401).adapter })).rejects.toThrow();

    expect(useAuthStore.getState().token).toBeNull();
    const target = new URL(location.href, 'http://app');
    expect(target.pathname).toBe('/login');
    expect(target.searchParams.get('redirect')).toBe('/components/mine?kind=tool');
    expect(target.searchParams.get('reason')).toBe('expired');
  });

  it('leaves a 401 without a session to the caller - e.g. a wrong login code', async () => {
    await expect(apiClient.post('/auth/otp/verify', {}, { adapter: server(401).adapter })).rejects.toThrow();
    expect(location.href).toBe('');
  });

  it('keeps the session on any other error', async () => {
    const valid = token();
    useAuthStore.getState().setToken(valid);

    await expect(apiClient.get('/components/x', { adapter: server(403).adapter })).rejects.toThrow();

    expect(useAuthStore.getState().token).toBe(valid);
    expect(location.href).toBe('');
  });
});

describe('apiClient', () => {
  it('unwraps the response body', async () => {
    await expect(apiClient.get('/stats', { adapter: server(200, { toolsPublished: 3 }).adapter })).resolves.toEqual({
      toolsPublished: 3,
    });
  });

  it('follows a HATEOAS link with its own method and target', async () => {
    const { adapter, sent } = server();
    const link = { rel: 'publish', href: '/components/1/commands', method: 'POST' } as const;

    await apiClient.request(link, { command: 'PUBLISH' }, { adapter });

    expect(sent[0].method).toBe('post');
    expect(sent[0].url).toBe('/components/1/commands');
    expect(JSON.parse(sent[0].data as string)).toEqual({ command: 'PUBLISH' });
  });

  it('names a download after the server, falling back when it says nothing', async () => {
    const blob = new Blob(['zip']);
    answerWith(server(200, blob, { 'content-disposition': 'attachment; filename="track-pipeline.zip"' }).adapter);
    await expect(apiClient.getBlob('/workflow-drafts/1/export', 'workflow.zip')).resolves.toEqual({
      blob,
      filename: 'track-pipeline.zip',
    });

    answerWith(server(200, blob).adapter);
    await expect(apiClient.getBlob('/x', 'workflow.zip')).resolves.toMatchObject({ filename: 'workflow.zip' });
  });

  it('reads the error a failed download sends as JSON, not as an opaque blob', async () => {
    const body = new Blob([JSON.stringify({ detail: 'Canvas is empty' })], { type: 'application/json' });
    answerWith(server(400, body).adapter);

    const error = await apiClient.getBlob('/workflow-drafts/1/export', 'w.zip').catch((e: AxiosError) => e);

    expect((error as AxiosError).response?.data).toEqual({ detail: 'Canvas is empty' });
  });
});

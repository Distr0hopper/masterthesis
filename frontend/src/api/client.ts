import axios, { type AxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/auth.store';

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Interceptor before request is send out - Attach JWT to request
axiosInstance.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Intercepting 401 - redirects to /login if not authenticated
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    // only force a redirect on session expiry (we had a token and it got rejected) —
    // a 401 from the login call itself just means wrong credentials and should be
    // handled by the caller, not treated as "you were logged out"
    if (error.response?.status === 401 && useAuthStore.getState().token) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// Thin wrapper that unwraps `res.data` once here, so service.ts callers get Promise<T> directly.
export const apiClient = {
  baseURL: axiosInstance.defaults.baseURL,
  get: <T>(url: string, config?: AxiosRequestConfig) =>
    axiosInstance.get<T>(url, config).then((res) => res.data),
  post: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance.post<T>(url, data, config).then((res) => res.data),
  patch: <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
    axiosInstance.patch<T>(url, data, config).then((res) => res.data),
  delete: <T>(url: string, config?: AxiosRequestConfig) =>
    axiosInstance.delete<T>(url, config).then((res) => res.data),
};
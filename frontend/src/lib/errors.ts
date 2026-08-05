import { AxiosError } from 'axios';

export function getErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (error instanceof AxiosError) {
    // backend's ErrorResponse serializes as { detail: "..." }
    const message = error.response?.data?.detail ?? error.response?.data?.message;
    if (Array.isArray(message)) return message.join(', ');
    if (typeof message === 'string') return message;
  }
  return fallback;
}
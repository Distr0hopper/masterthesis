export function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Date and local time - for deadlines, where the hour matters (e.g. "22 Oct 2026, 10:00"). */
export function formatDateTime(date: Date): string {
  return date.toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
}

export interface Creator {
  firstName: string | null;
  lastName: string | null;
  email: string;
}

export function getCreatorDisplay(creator: Creator | null): string {
  if (!creator) return 'Unknown';
  const { firstName, lastName, email } = creator;
  return firstName && lastName ? `${firstName} ${lastName}` : email;
}

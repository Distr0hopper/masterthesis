export function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10);
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
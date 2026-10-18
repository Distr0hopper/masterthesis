/** `isoString`'s age as a short label - `just now`, `5m ago`, `2h ago`, `3d ago`. An
 * unparseable timestamp reads as `just now` rather than `NaNd ago`. */
export function formatRelativeTime(isoString: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (!Number.isFinite(seconds) || seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86_400)}d ago`;
}

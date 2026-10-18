import { useEffect, useState } from 'react';
import { formatRelativeTime } from './relativeTime';

const REFRESH_MS = 60_000;

/**
 * formatRelativeTime for `isoString`, kept current while mounted - the label never shows
 * finer than minutes, so it re-renders once a minute. null while there is no timestamp.
 */
export function useRelativeTime(isoString: string | null): string | null {
  const [label, setLabel] = useState<string | null>(null);

  useEffect(() => {
    if (!isoString) {
      setLabel(null);
      return;
    }

    const update = () => setLabel(formatRelativeTime(isoString));
    update();
    const interval = setInterval(update, REFRESH_MS);
    return () => clearInterval(interval);
  }, [isoString]);

  return label;
}

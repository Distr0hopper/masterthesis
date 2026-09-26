import { useEffect, useState } from 'react';

interface LoadMoreOptions {
  hasNextPage: boolean | undefined;
  isFetchingNextPage: boolean;
  fetchNextPage: () => unknown;
}

/**
 * Loads the next page of an infinite query once the end of a scrollable list comes into
 * view. Put `scrollRef` on the scrolling container and `sentinelRef` on an empty element
 * after the last item.
 *
 * The refs are callback refs kept in state rather than useRef, so the observer is set up
 * whenever the elements mount - also when they mount *after* the data (a dialog opening
 * over an already-cached first page), which a plain ref would never re-run for.
 */
export function useLoadMoreOnScroll({ hasNextPage, isFetchingNextPage, fetchNextPage }: LoadMoreOptions) {
  const [scrollElement, scrollRef] = useState<HTMLElement | null>(null);
  const [sentinel, sentinelRef] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!sentinel || !hasNextPage) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !isFetchingNextPage) void fetchNextPage();
      },
      // start loading a little before the bottom is actually reached
      { root: scrollElement, rootMargin: '200px' },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [scrollElement, sentinel, hasNextPage, isFetchingNextPage, fetchNextPage]);

  return { scrollRef, sentinelRef };
}

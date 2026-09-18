import { usePageParams } from './usePageParams';

interface SplitPageParamsBucket {
  limit: number;
  offset: number;
  setOffset: (offset: number) => void;
  /** 1-based, for <Pagination currentPage> */
  page: number;
  goToPage: (page: number) => void;
}

interface UseSplitPageParamsResult {
  limit: number;
  published: SplitPageParamsBucket;
  unpublished: SplitPageParamsBucket;
}

/**
 * URL-backed pagination for a page with two independently paged sections (My Workflows,
 * My Components). Both buckets read the same shared `limit` key but own a distinct offset
 * key, matching the `publishedOffset`/`unpublishedOffset` params the `/mine` endpoints take.
 */
export function useSplitPageParams(): UseSplitPageParamsResult {
  const published = usePageParams({ offsetKey: 'publishedOffset' });
  const unpublished = usePageParams({ offsetKey: 'unpublishedOffset' });

  const toBucket = (params: ReturnType<typeof usePageParams>): SplitPageParamsBucket => ({
    limit: params.limit,
    offset: params.offset,
    setOffset: params.setOffset,
    page: Math.floor(params.offset / params.limit) + 1,
    goToPage: (page: number) => params.setOffset((page - 1) * params.limit),
  });

  return {
    limit: published.limit,
    published: toBucket(published),
    unpublished: toBucket(unpublished),
  };
}

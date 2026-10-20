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
  deprecated: SplitPageParamsBucket;
}

/**
 * URL-backed pagination for a page with independently paged sections (My
 * Components). Every bucket reads the same shared `limit` key but owns a distinct offset
 * key, matching the `publishedOffset`/`unpublishedOffset`/`deprecatedOffset` params `/mine` takes.
 */
export function useSplitPageParams(): UseSplitPageParamsResult {
  const published = usePageParams({ offsetKey: 'publishedOffset' });
  const unpublished = usePageParams({ offsetKey: 'unpublishedOffset' });
  const deprecated = usePageParams({ offsetKey: 'deprecatedOffset' });

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
    deprecated: toBucket(deprecated),
  };
}

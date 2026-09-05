import { useSearchParams } from 'react-router-dom';

interface UsePageParamsOptions {
  defaultLimit?: number;
  /** overridable so a page can own more than one paginated list against the same URL (e.g. MyWorkflowsPage) */
  offsetKey?: string;
}

interface UsePageParamsResult {
  limit: number;
  offset: number;
  setOffset: (offset: number) => void;
  getFilter: (key: string) => string;
  /** setting a filter always resets this list's offset back to 0 */
  setFilter: (key: string, value: string) => void;
}

export function usePageParams(options: UsePageParamsOptions = {}): UsePageParamsResult {
  const { defaultLimit = 10, offsetKey = 'offset' } = options;
  const [searchParams, setSearchParams] = useSearchParams();

  const limit = Number(searchParams.get('limit')) || defaultLimit;
  const offset = Number(searchParams.get(offsetKey)) || 0;

  const setOffset = (next: number) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      params.set(offsetKey, String(next));
      return params;
    });
  };

  const getFilter = (key: string) => searchParams.get(key) ?? '';

  const setFilter = (key: string, value: string) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev);
      if (value) params.set(key, value);
      else params.delete(key);
      params.set(offsetKey, '0');
      return params;
    });
  };

  return { limit, offset, setOffset, getFilter, setFilter };
}

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface HateoasLink {
  href: string;
  method: HttpMethod;
}

export type HateoasLinks = Record<string, HateoasLink>;

export type StandardAction =
  | 'self'
  | 'update'
  | 'delete'
  | 'create'
  | 'list'
  | 'validate'
  | 'approve'
  | 'reject';

export interface WithHateoasLinks {
  _links?: HateoasLinks;
}

export interface PageResponse<T> {
  content: T[];
  limit: number;
  offset: number;
  totalPages: number;
  totalElements: number;
}

/**
 * The "my <entity>" response shape shared by GET /workflows/mine and GET /components/mine -
 * two independently paginated buckets the server splits by publication status.
 */
export interface SplitPageResponse<T> {
  published: PageResponse<T>;
  unpublished: PageResponse<T>;
}

export interface SplitDisplayModel<T> {
  published: ListDisplayModel<T>;
  unpublished: ListDisplayModel<T>;
}

export interface MineQueryParams {
  limit?: number;
  publishedOffset?: number;
  unpublishedOffset?: number;
}

export interface ListDisplayModel<T> {
  items: T[];
  total: number;
  totalPages: number;
  limit: number;
  offset: number;
}

export interface PageParams<T> {
  limit?: number;
  offset?: number;
  sortBy?: keyof T;
  sortDirection?: 'asc' | 'desc';
}

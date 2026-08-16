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

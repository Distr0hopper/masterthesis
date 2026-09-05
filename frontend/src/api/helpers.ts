import type { ListDisplayModel, PageResponse } from '@/api/types';

export function toListDisplayModel<TDto, TDisplay>(
  response: PageResponse<TDto>,
  dtoListToDisplayModels: (dtos: TDto[]) => TDisplay[],
): ListDisplayModel<TDisplay> {
  return {
    items: dtoListToDisplayModels(response.content),
    total: response.totalElements,
    totalPages: response.totalPages,
    limit: response.limit,
    offset: response.offset,
  };
}

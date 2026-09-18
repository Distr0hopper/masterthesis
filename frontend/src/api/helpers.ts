import type { ListDisplayModel, PageResponse, SplitDisplayModel, SplitPageResponse } from '@/api/types';

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

/** toListDisplayModel applied to both buckets of a SplitPageResponse. */
export function toSplitDisplayModel<TDto, TDisplay>(
  response: SplitPageResponse<TDto>,
  dtoListToDisplayModels: (dtos: TDto[]) => TDisplay[],
): SplitDisplayModel<TDisplay> {
  return {
    published: toListDisplayModel(response.published, dtoListToDisplayModels),
    unpublished: toListDisplayModel(response.unpublished, dtoListToDisplayModels),
  };
}

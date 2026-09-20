import type { HateoasLink, HateoasLinks, StandardAction } from './types';

export const hasLink = (links: HateoasLinks | undefined | null, action: StandardAction | string): boolean => {
  if (!links) return false;
  return action in links;
};

export const hasAllLinks = (links: HateoasLinks | undefined | null, actions: (StandardAction | string)[]): boolean => {
  if (!links) return false;
  return actions.every((action) => action in links);
};

export const hasAnyLink = (links: HateoasLinks | undefined | null, actions: (StandardAction | string)[]): boolean => {
  if (!links) return false;
  return actions.some((action) => action in links);
};

export const getLink = (
  links: HateoasLinks | undefined | null,
  action: StandardAction | string,
): HateoasLink | undefined => {
  if (!links) return undefined;
  return links[action];
};

export const getAvailableActions = (links: HateoasLinks | undefined | null): string[] => {
  if (!links) return [];
  return Object.keys(links);
};

export const canView = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'self');

export const canUpdate = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'update');

export const canDelete = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'delete');

export const canFavorite = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'favorite');

export const canUnfavorite = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'unfavorite');

export const canPublish = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'publish');

export const canUnpublish = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'unpublish');

export const canUpdateDescription = (links: HateoasLinks | undefined | null): boolean =>
  hasLink(links, 'updateDescription');

export const canUpdateDomain = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'updateDomain');

export const canConfirm = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'confirm');

export const canRepackage = (links: HateoasLinks | undefined | null): boolean => hasLink(links, 'repackage');

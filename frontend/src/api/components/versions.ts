import { ComponentStatus } from './types';

/** A lineage's versions, newest first - the order every version list shows them in. */
export function newestFirst<T extends { version: number }>(versions: T[]): T[] {
  return [...versions].sort((a, b) => b.version - a.version);
}

/** The version the catalogue lists - what "latest" means to everyone else. */
export function latestPublished<T extends { version: number; status: ComponentStatus }>(versions: T[]): T | undefined {
  return newestFirst(versions).find((v) => v.status === ComponentStatus.PUBLISHED);
}

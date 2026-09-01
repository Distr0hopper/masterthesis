export function buildDockerPullUrl(reference: string): string | null {
  const trimmed = reference.trim();
  if (!trimmed) return null;

  // Strip a @sha256:... digest first, before any ':' tag-splitting, so the
  // digest's own colon can't be mistaken for a tag separator.
  const withoutDigest = trimmed.split('@')[0].trim();
  if (!withoutDigest) return null;

  const segments = withoutDigest.split('/').filter(Boolean);
  if (segments.length === 0) return null;

  // A registry host is only distinguishable from a bare image name once there's
  // at least one '/' - "python:3.9" has no slash, so its ':' is always a tag
  // separator, never a port. Only treat the first segment as host-like when
  // there's more than one path component (mirrors Docker's own reference
  // parsing rule).
  const hasExplicitHost =
    segments.length > 1 && (segments[0].includes('.') || segments[0].includes(':') || segments[0] === 'localhost');

  if (hasExplicitHost) {
    // Best-effort landing page only - registry-specific deep link paths aren't
    // reliably derivable across arbitrary registries. Keep the port if present.
    return `https://${segments[0]}`;
  }

  // No explicit host -> implicit Docker Hub. Strip a trailing ":tag" from the
  // last path segment only.
  const lastSegment = segments[segments.length - 1];
  const colonIndex = lastSegment.lastIndexOf(':');
  const name = colonIndex === -1 ? lastSegment : lastSegment.slice(0, colonIndex);
  if (!name) return null;

  if (segments.length === 1) {
    // official image, e.g. "python:3.9" -> "python"
    return `https://hub.docker.com/_/${name}`;
  }

  if (segments.length === 2) {
    // user/org image, e.g. "myorg/myimage:latest" -> "myorg/myimage"
    return `https://hub.docker.com/r/${segments[0]}/${name}`;
  }

  // More than one '/' with no host-like first segment is non-standard for
  // Docker Hub (which only supports single-level namespaces). Treat the first
  // two segments as namespace/name rather than returning null - degrades
  // gracefully instead of hiding the link for an unlikely format surprise.
  return `https://hub.docker.com/r/${segments[0]}/${segments[1]}`;
}

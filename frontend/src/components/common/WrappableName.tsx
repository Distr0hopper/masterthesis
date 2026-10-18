import { Fragment } from 'react';

/** `GraphComponentsTool` -> `Graph|Components|Tool`: the points a long identifier may wrap at
 * (before an inner capital, after `_`/`-`/`.`), so it never breaks mid-word. */
const WRAP_POINTS = /(?<=[a-z0-9])(?=[A-Z])|(?<=[_\-.])/;

interface WrappableNameProps {
  name: string;
}

/**
 * An identifier (component, parameter or file name) that wraps at its word boundaries
 * instead of mid-word. Inline and unstyled - pair it with `break-words` on the parent so
 * a single overlong part can still split rather than overflow.
 */
export function WrappableName({ name }: WrappableNameProps) {
  return name.split(WRAP_POINTS).map((part, i) => (
    <Fragment key={i}>
      {i > 0 && <wbr />}
      {part}
    </Fragment>
  ));
}

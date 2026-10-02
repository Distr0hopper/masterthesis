import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Loader2, Package, Search, Workflow } from 'lucide-react';
import { useGlobalSearch } from '@/api/search';
import { useDebouncedValue } from '@/lib/useDebouncedValue';
import { ROUTES } from '@/lib/routes';
import { cn } from '@/lib/utils';

interface GlobalSearchProps {
  /** compact: the navbar field; large: the Home hero, where the field has room of its own */
  size?: 'compact' | 'large';
  /** the compact phone variant opens already focused */
  autoFocus?: boolean;
  enableShortcut?: boolean;
  /** called after a result is opened or Escape is pressed - not on a click outside, which
   *  only hides the dropdown (that click may be the very button that toggles this search) */
  onClose?: () => void;
  className?: string;
}

interface Entry {
  key: string;
  to: string;
  content: ReactNode;
}

/** true when the key press happens inside a field that takes text itself */
function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
}

/**
 * Navbar search across tools and workflows. Results stay grouped by kind - the two
 * lists are kept apart on purpose - and each group links to its full, filtered list.
 */
export function GlobalSearch({ size = 'compact', autoFocus, enableShortcut, onClose, className }: GlobalSearchProps) {
  const large = size === 'large';
  const navigate = useNavigate();
  const location = useLocation();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxId = useId();

  const [term, setTerm] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const debouncedTerm = useDebouncedValue(term, 250);
  const search = debouncedTerm.trim();
  const { tools, workflows, isFetching, isReady } = useGlobalSearch(search);

  const hideResults = () => {
    setOpen(false);
    setActiveIndex(-1);
  };

  const close = () => {
    hideResults();
    onClose?.();
  };

  // any navigation - a result, "Show all", or elsewhere - ends the search
  useEffect(() => {
    setTerm('');
    setOpen(false);
    setActiveIndex(-1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.key]);

  // a click anywhere outside dismisses the dropdown
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) hideResults();
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!enableShortcut) return;
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      const commandK = event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey);
      const slash = event.key === '/' && !isTypingTarget(event.target);
      if (!commandK && !slash) return;
      // a hidden (display: none) input can't take focus - leave the key alone then
      if (!inputRef.current?.offsetParent) return;
      event.preventDefault();
      inputRef.current.focus();
      inputRef.current.select();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [enableShortcut]);

  const toolsListUrl = `${ROUTES.tools}?search=${encodeURIComponent(search)}`;
  const workflowsListUrl = `${ROUTES.workflows}?search=${encodeURIComponent(search)}`;

  // one flat list, in display order, so the arrow keys can walk across both groups
  const toolEntries: Entry[] = tools.items.map((c) => ({
    key: `c-${c.id}`,
    to: ROUTES.toolDetail(c.id),
    content: (
      <ResultLine icon={<Package className="h-4 w-4" />} title={c.name} meta={`v${c.version}`} detail={c.description} />
    ),
  }));
  const workflowEntries: Entry[] = workflows.items.map((w) => ({
    key: `w-${w.id}`,
    to: ROUTES.workflowDetail(w.id),
    content: (
      <ResultLine
        icon={<Workflow className="h-4 w-4" />}
        title={w.name}
        meta={`${w.stepCount} step${w.stepCount === 1 ? '' : 's'}`}
        detail={w.description}
      />
    ),
  }));
  const showAll = (label: string, total: number, to: string, key: string): Entry => ({
    key,
    to,
    content: (
      <span className="text-xs font-medium text-jmu-blue-800">
        Show all {label} ({total}) →
      </span>
    ),
  });

  const groups = [
    { title: 'Tools', entries: toolEntries, all: showAll('tools', tools.total, toolsListUrl, 'c-all') },
    { title: 'Workflows', entries: workflowEntries, all: showAll('workflows', workflows.total, workflowsListUrl, 'w-all') },
  ].filter((group) => group.entries.length > 0);
  const flat = groups.flatMap((group) => [...group.entries, group.all]);

  const openEntry = (entry: Entry | undefined) => {
    if (!entry) return;
    navigate(entry.to);
    inputRef.current?.blur();
    close();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      inputRef.current?.blur();
      close();
    } else if (event.key === 'ArrowDown' && flat.length > 0) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((i) => (i + 1) % flat.length);
    } else if (event.key === 'ArrowUp' && flat.length > 0) {
      event.preventDefault();
      setActiveIndex((i) => (i <= 0 ? flat.length - 1 : i - 1));
    } else if (event.key === 'Enter') {
      event.preventDefault();
      // no row picked: the first group's full list is the natural "search for this"
      openEntry(activeIndex >= 0 ? flat[activeIndex] : groups[0]?.all);
    }
  };

  const showDropdown = open && term.trim().length > 0;
  const noResults = isReady && !isFetching && groups.length === 0;
  const optionId = (index: number) => `${listboxId}-option-${index}`;

  let index = -1;
  return (
    <div ref={containerRef} className={cn('group relative', className)}>
      <Search
        className={cn(
          'pointer-events-none absolute top-1/2 -translate-y-1/2 text-jmu-blue-200 group-focus-within:text-slate-400',
          large ? 'left-3.5 h-5 w-5' : 'left-2.5 h-4 w-4',
        )}
      />
      <input
        ref={inputRef}
        type="search"
        role="combobox"
        aria-label="Search components and workflows"
        aria-expanded={showDropdown}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={activeIndex >= 0 ? optionId(activeIndex) : undefined}
        autoFocus={autoFocus}
        value={term}
        // the navbar leaves ~145px for its field - the aria-label carries the full wording there
        placeholder={large ? 'Search components & workflows…' : 'Search…'}
        onChange={(e) => {
          setTerm(e.target.value);
          setOpen(true);
          setActiveIndex(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        className={cn(
          'w-full rounded-md border border-white/20 bg-white/10 text-white placeholder:text-jmu-blue-200 focus:border-white focus:bg-white focus:text-slate-900 focus:placeholder:text-slate-400 focus:outline-none',
          large ? 'h-12 pl-11 pr-11 text-base' : 'h-8 pl-8 pr-10 text-sm',
        )}
      />
      {enableShortcut && !term && (
        <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-white/30 px-1.5 text-[10px] text-jmu-blue-200 group-focus-within:hidden">
          /
        </kbd>
      )}
      {isFetching && term && (
        <Loader2
          className={cn(
            'absolute top-1/2 -translate-y-1/2 animate-spin text-slate-400',
            large ? 'right-4 h-5 w-5' : 'right-2.5 h-4 w-4',
          )}
        />
      )}

      {showDropdown && (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Search results"
          // compact: wider than the field and anchored to its right edge - the results need
          // room the navbar can't give the field, so the popup opens leftwards over the nav.
          // large: the field is wide enough, so the popup simply matches it
          className={cn(
            'absolute right-0 top-full z-50 mt-2 max-h-[70vh] overflow-y-auto rounded-md border border-slate-200 bg-white py-1 text-slate-900 shadow-lg',
            large ? 'left-0' : 'w-[26rem] max-w-[calc(100vw-2rem)]',
          )}
        >
          {!isReady && groups.length === 0 ? (
            <p className="px-3 py-2 text-sm text-slate-500">Searching...</p>
          ) : noResults ? (
            <p className="px-3 py-2 text-sm text-slate-500">
              No components or workflows match &ldquo;{search}&rdquo;.
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.title} role="group" aria-label={group.title} className="py-1">
                <p className="px-3 pb-1 pt-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  {group.title}
                </p>
                {[...group.entries, group.all].map((entry) => {
                  index += 1;
                  const current = index;
                  return (
                    <div
                      key={entry.key}
                      id={optionId(current)}
                      role="option"
                      aria-selected={current === activeIndex}
                      onPointerDown={(e) => e.preventDefault() /* keep focus in the input */}
                      onPointerEnter={() => setActiveIndex(current)}
                      onClick={() => openEntry(entry)}
                      className={cn('cursor-pointer px-3 py-1.5', current === activeIndex && 'bg-slate-100')}
                    >
                      {entry.content}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function ResultLine({
  icon,
  title,
  meta,
  detail,
}: {
  icon: ReactNode;
  title: string;
  meta: string;
  detail: string | null;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-0.5 shrink-0 text-slate-400">{icon}</span>
      <div className="min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="truncate font-mono text-sm font-semibold">{title}</span>
          <span className="shrink-0 text-xs text-slate-400">{meta}</span>
        </div>
        {detail && <p className="line-clamp-1 text-xs text-slate-500">{detail}</p>}
      </div>
    </div>
  );
}

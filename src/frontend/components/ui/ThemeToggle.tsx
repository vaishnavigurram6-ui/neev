'use client';

// The `data-theme` attribute on <html> is the source of truth — it is set before
// first paint by the inline script in the root layout, so React must read it
// rather than own it. useSyncExternalStore subscribes to that attribute; a
// useEffect + setState pair would fight the pre-paint script and trips Next 16's
// react-hooks/set-state-in-effect rule.
import { useSyncExternalStore } from 'react';

type Theme = 'light' | 'dark';

function subscribe(onStoreChange: () => void): () => void {
  const observer = new MutationObserver(onStoreChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme'],
  });
  return () => observer.disconnect();
}

function getSnapshot(): Theme {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
}

/** The server cannot know the viewer's theme; hydration corrects this. */
function getServerSnapshot(): Theme {
  return 'light';
}

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const label = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';

  const toggle = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try {
      localStorage.setItem('neev-theme', next);
    } catch {
      // Private browsing or blocked storage: the toggle still works this session.
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={theme === 'dark'}
      title={label}
      className="flex h-[30px] w-[30px] items-center justify-center rounded-lg border border-input-border bg-card text-[13px] text-sub hover:text-ink"
    >
      <span aria-hidden="true">◐</span>
      <span className="sr-only">{label}</span>
    </button>
  );
}

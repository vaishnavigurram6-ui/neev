// Spec §6.7: the accessibility cluster is specified as functional, not
// decorative — the handoff says "mocked in prototype, must be functional in
// build". In this build the theme toggle works app-wide; the language switcher
// and listen-aloud render with correct semantics and a disabled state that says
// why, since translation and TTS are out of scope. A disabled control that
// announces the reason beats a dead control that lies.
import ThemeToggle from './ThemeToggle';

const OUT_OF_SCOPE = 'Coming soon — this build is English only.';

export default function AccessibilityCluster() {
  return (
    <div className="flex items-center gap-[6px]">
      <button
        type="button"
        disabled
        aria-disabled="true"
        title={`Language: English / हिंदी / తెలుగు. ${OUT_OF_SCOPE}`}
        className="rounded-lg border border-input-border bg-card px-[10px] py-[6px] text-[12px] font-semibold text-sub opacity-55"
      >
        EN <span aria-hidden="true">▾</span>
        <span className="sr-only">. {OUT_OF_SCOPE}</span>
      </button>
      <button
        type="button"
        disabled
        aria-disabled="true"
        title={`Listen to this page. ${OUT_OF_SCOPE}`}
        className="flex h-[30px] w-[30px] items-center justify-center rounded-lg border border-input-border bg-card text-[13px] opacity-55"
      >
        <span aria-hidden="true">🔊</span>
        <span className="sr-only">Listen to this page. {OUT_OF_SCOPE}</span>
      </button>
      <ThemeToggle />
    </div>
  );
}

// The site-evidence grid: one wide frame beside two smaller ones, exactly the
// prototype's `2fr 1fr / 150px 150px` arrangement.
//
// Not `PhotoSlot`: that component is the owner's *upload* control — a file input,
// a client-side downscale, a live preview. This is the lender's read-only view of
// photographs that already exist, and putting a file input on a decision screen
// would invite the officer to add evidence to the borrower's own submission.
//
// A `PhotoView` carries `src` when the frame itself is held — a photograph the
// borrower sent through Update Progress — and null when the row records only
// what the visual inspector read, which is what the seeded inspection notes
// are. Both render: the frame when there is one, the caption always, because
// the caption is the pipeline's reading of the photograph and the part an
// officer acts on.
import type { EvidenceChipView, PhotoView } from '@/lib/types';

const NO_IMAGE = 'Photograph on file';

export default function EvidenceGrid({ photos }: { photos: PhotoView[] }) {
  return (
    <ul className="grid grid-cols-[2fr_1fr] grid-rows-[150px_150px] gap-[10px]">
      {photos.map((photo, index) => (
        <li
          key={photo.slot_key}
          // The first photograph is the wide-angle frame and spans both rows,
          // as in the prototype. Anything past the third is laid out normally
          // rather than dropped.
          className={`relative flex flex-col justify-end overflow-hidden rounded-bank border border-line bg-chip p-3 ${
            index === 0 ? 'row-span-2' : ''
          }`}
        >
          {photo.src ? (
            <>
              {/* Plain <img>: these are private, session-gated bytes behind a
                  relay, so Next's optimiser has nothing to cache and would
                  only add a hop that needs the same cookie. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.src}
                alt={photo.caption ?? 'Site photograph sent by the borrower'}
                loading="lazy"
                className="absolute inset-0 h-full w-full object-cover"
              />
              {photo.caption && (
                <span className="relative bg-scrim px-2 py-[6px] text-[12px] leading-[1.45] text-on-scrim">
                  {photo.caption}
                </span>
              )}
            </>
          ) : (
            <>
              <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint">
                {NO_IMAGE}
              </span>
              {photo.caption && (
                <span className="mt-[4px] text-[12px] leading-[1.45] text-sub">
                  {photo.caption}
                </span>
              )}
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

/** The chip row under the grid, as the prototype has it: one row of checks for
 *  the set, not the same three chips repeated on every frame.
 *
 *  Deduplicated by label rather than assumed identical — if one photograph's
 *  geotag failed while the others matched, both chips appear, which is the
 *  reading an officer needs and the one a "first photo wins" shortcut would
 *  hide. */
export function evidenceChips(photos: PhotoView[]): EvidenceChipView[] {
  const seen = new Map<string, EvidenceChipView>();
  for (const photo of photos) {
    for (const chip of photo.chips) {
      if (!seen.has(chip.label)) seen.set(chip.label, chip);
    }
  }
  return [...seen.values()];
}

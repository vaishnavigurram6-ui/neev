// The site-evidence grid: one wide frame beside two smaller ones, exactly the
// prototype's `2fr 1fr / 150px 150px` arrangement.
//
// Not `PhotoSlot`: that component is the owner's *upload* control — a file input,
// a client-side downscale, a live preview. This is the lender's read-only view of
// photographs that already exist, and putting a file input on a decision screen
// would invite the officer to add evidence to the borrower's own submission.
//
// `PhotoView` carries no image URL in this build (nothing is stored yet), so each
// frame renders its caption — which is the pipeline's actual reading of the
// photograph, and the part an officer acts on.
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
          className={`flex flex-col justify-end overflow-hidden rounded-bank border border-line bg-chip p-3 ${
            index === 0 ? 'row-span-2' : ''
          }`}
        >
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint">
            {NO_IMAGE}
          </span>
          {photo.caption && (
            <span className="mt-[4px] text-[12px] leading-[1.45] text-sub">{photo.caption}</span>
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

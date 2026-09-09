// The Landing hero's photograph.
//
// The kit's <PhotoSlot> is not the right component here: it is an upload
// control with a file input, a downscaler and an aria-live status, built for
// site photos on the owner's milestone screens. The hero needs the same shape
// with none of the behaviour.
//
// It keeps the empty slot it started as. `src` is optional, and without one it
// renders the placeholder box the handoff shipped with — the prototype carries
// no binary assets, so a screen composed from the kit alone still lays out.
import Image from 'next/image';

/** The asset's own pixels, so the box reserves its space before the file
 *  arrives and the headline beside it never jumps. */
const WIDTH = 1400;
const HEIGHT = 990;

export default function HeroPhoto({
  placeholder,
  src,
  alt,
}: {
  /** Describes the photograph that belongs here. Shown when there is none. */
  placeholder: string;
  src?: string;
  /** What the photograph shows. Required alongside `src`: this is the first
   *  thing on the public page, and `placeholder` describes the slot's brief
   *  rather than the image that ended up in it. */
  alt?: string;
}) {
  if (!src) {
    return (
      <div
        role="img"
        aria-label={placeholder}
        className="flex h-[380px] w-full items-center justify-center overflow-hidden rounded-[22px] border border-line bg-chip"
      >
        <p aria-hidden="true" className="max-w-[24ch] px-6 text-center text-[12.5px] text-faint">
          {placeholder}
        </p>
      </div>
    );
  }

  return (
    <div className="relative h-[380px] w-full overflow-hidden rounded-[22px] border border-line bg-chip">
      <Image
        src={src}
        alt={alt ?? placeholder}
        width={WIDTH}
        height={HEIGHT}
        // The first thing above the fold on the one page that loads no data:
        // it should not wait for anything.
        priority
        // Already sized and compressed at build time (153 KB), and the
        // standalone server ships without sharp — an optimiser that is not
        // there would leave the hero broken in the container rather than
        // merely unoptimised.
        unoptimized
        className="h-full w-full object-cover object-center"
      />
    </div>
  );
}

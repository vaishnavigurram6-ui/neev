// The Landing hero's photo area — the one place the prototype's <image-slot>
// appears on a public page.
//
// The kit's <PhotoSlot> is not the right component here: it is an upload control
// with a file input, a downscaler and an aria-live status, built for site photos
// on the owner's milestone screens. The hero needs the same shape with none of
// the behaviour, so this is the slot without the input. When a real photograph
// exists it replaces the placeholder here and nowhere else — the handoff ships
// no binary assets.
export default function HeroPhoto({ placeholder }: { placeholder: string }) {
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

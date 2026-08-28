// Dropzone.tsx — a real file input with a real label. The prototype's dropzone
// is a div; ported literally it would be unreachable by keyboard.
export default function Dropzone({
  name,
  accept,
  label,
  hint,
  multiple = false,
}: {
  name: string;
  accept: string;
  label: string;
  hint: string;
  multiple?: boolean;
}) {
  const id = `dz-${name}`;
  return (
    <div className="rounded-card border-2 border-dashed border-line bg-card px-6 py-9 text-center">
      <label htmlFor={id} className="cursor-pointer">
        <span className="block font-display text-[16px] font-semibold text-ink">{label}</span>
        <span className="mt-[6px] block text-[12.5px] text-sub">{hint}</span>
      </label>
      <input
        id={id}
        name={name}
        type="file"
        accept={accept}
        multiple={multiple}
        className="mx-auto mt-4 block text-[12.5px] text-sub file:mr-3 file:rounded-pill file:border-0 file:bg-action file:px-4 file:py-2 file:text-[12.5px] file:font-semibold file:text-card hover:file:bg-action-hover"
      />
    </div>
  );
}

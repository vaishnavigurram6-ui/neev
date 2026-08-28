'use client';

// Dropzone.tsx — a real file input with a real label. The prototype's dropzone
// is a div; ported literally it would be unreachable by keyboard.
//
// It also has to actually accept a drop. Dashed-border drop-target styling
// invites the gesture, and without handlers the browser default takes over:
// the page navigates away to the dropped file's URL and any form state the
// owner had entered is gone. So the drop is caught, and the file is handed to
// the real <input> so one code path — the input's value — carries the upload.
import { useRef, useState } from 'react';

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
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [over, setOver] = useState(false);
  const [picked, setPicked] = useState<string>('');

  const describe = (files: FileList | null) => {
    if (!files || files.length === 0) return setPicked('');
    setPicked(
      files.length === 1 ? `${files[0].name} selected` : `${files.length} files selected`
    );
  };

  const onDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setOver(false);
    const input = inputRef.current;
    const dropped = event.dataTransfer.files;
    if (!input || dropped.length === 0) return;
    const transfer = new DataTransfer();
    for (const file of Array.from(dropped).slice(0, multiple ? dropped.length : 1)) {
      transfer.items.add(file);
    }
    input.files = transfer.files;
    describe(input.files);
    // Assigning .files does not fire change; tell any listening form it did.
    input.dispatchEvent(new Event('change', { bubbles: true }));
  };

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      className={`rounded-card border-2 border-dashed px-6 py-9 text-center transition-colors ${
        over ? 'border-action bg-hover' : 'border-line bg-card'
      }`}
    >
      <label htmlFor={id} className="cursor-pointer">
        <span className="block font-display text-[16px] font-semibold text-ink">{label}</span>
        <span className="mt-[6px] block text-[12.5px] text-sub">{hint}</span>
      </label>
      <input
        ref={inputRef}
        id={id}
        name={name}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={(event) => describe(event.target.files)}
        className="mx-auto mt-4 block text-[12.5px] text-sub file:mr-3 file:rounded-pill file:border-0 file:bg-action file:px-4 file:py-2 file:text-[12.5px] file:font-semibold file:text-on-action hover:file:bg-action-hover"
      />
      <p aria-live="polite" className="mt-[8px] text-[11.5px] text-faint">
        {picked}
      </p>
    </div>
  );
}

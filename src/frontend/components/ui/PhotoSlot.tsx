'use client';

// PhotoSlot.tsx — replaces the prototype's image-slot.js, which stored data-URLs
// in a sidecar JSON via window.omelette: pure design-runtime infrastructure with
// no production role. Three of its behaviours are kept — client-side downscale
// before upload, the image accept-list, and a fit notion for same-angle
// comparison. The 12 slot ids across 4 screens become {loanId, tranche, slotKey}.
import Image from 'next/image';
import { useEffect, useId, useRef, useState } from 'react';
import StatusPill from './StatusPill';
import type { Tone } from '@/lib/tone';

const ACCEPT = 'image/png,image/jpeg,image/webp,image/avif';
const MAX_EDGE = 1600;

export default function PhotoSlot({
  slotKey,
  label,
  guidance,
  chips = [],
  onFile,
}: {
  slotKey: string;
  label: string;
  guidance?: string;
  chips?: { label: string; tone: Tone }[];
  onFile?: (file: File) => void;
}) {
  const inputId = useId();
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState('No photo yet');
  // Object URLs are revoked when replaced and on unmount; otherwise every
  // re-pick leaks the previous blob for the life of the document.
  const previewRef = useRef<string | null>(null);
  // Downscaling is async and its duration depends on the photo, so two quick
  // picks can resolve out of order. Without this counter the slower first pick
  // would land last: it would revoke the URL currently on screen and then set
  // its own older photo as the preview while the parent had already been handed
  // the newer file. On a screen whose entire purpose is tying a milestone to the
  // right site photo, the preview and the queued upload must never disagree.
  const generation = useRef(0);

  useEffect(
    () => () => {
      // Bump so an in-flight downscale that resolves after unmount bails out
      // rather than creating an object URL nothing will ever revoke.
      generation.current += 1;
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    },
    []
  );

  const handle = async (file: File | undefined) => {
    if (!file) return;
    const mine = (generation.current += 1);
    setStatus(`Preparing ${file.name}…`);
    const downscaled = await downscale(file);

    if (mine !== generation.current) return; // superseded, or unmounted

    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    const url = URL.createObjectURL(downscaled);
    previewRef.current = url;
    setPreview(url);
    setStatus(`${file.name} ready to upload`);
    onFile?.(new File([downscaled], uploadName(file.name, downscaled.type), {
      type: downscaled.type,
    }));
  };

  return (
    <div className="rounded-card border border-line bg-card p-3">
      <label htmlFor={inputId} className="block text-[12.5px] font-semibold text-ink">
        {label}
      </label>
      {guidance && <p className="mt-[3px] text-[11px] text-sub">{guidance}</p>}

      <div className="mt-[10px] flex aspect-[4/3] items-center justify-center overflow-hidden rounded-[10px] bg-chip">
        {preview ? (
          <Image
            src={preview}
            alt={`${label} — uploaded site photo`}
            width={MAX_EDGE}
            height={(MAX_EDGE * 3) / 4}
            className="h-full w-full object-cover"
            unoptimized
          />
        ) : (
          <span className="text-[11.5px] text-faint">Same spot, every month</span>
        )}
      </div>

      <input
        id={inputId}
        type="file"
        accept={ACCEPT}
        data-slot-key={slotKey}
        onChange={(event) => void handle(event.target.files?.[0])}
        className="mt-[10px] block w-full text-[11.5px] text-sub"
      />
      {/* Upload status is announced, not merely shown. */}
      <p aria-live="polite" className="mt-[6px] text-[11px] text-faint">
        {status}
      </p>

      {chips.length > 0 && (
        <div className="mt-[8px] flex flex-wrap gap-[6px]">
          {chips.map((chip) => (
            <StatusPill key={chip.label} tone={chip.tone} label={chip.label} size="sm" />
          ))}
        </div>
      )}
    </div>
  );
}

/** Keep the filename honest about what the bytes are. `downscale()` re-encodes
 *  to JPEG, so a downscaled `site.png` must not be uploaded as `site.png` —
 *  extension-based validation or an extension-derived storage key on the backend
 *  would reject it, or store a `.png` that is really a JPEG. */
function uploadName(original: string, type: string): string {
  if (type !== 'image/jpeg') return original;
  return original.replace(/\.[^./\\]+$/, '') + '.jpg';
}

/** Downscale to MAX_EDGE before upload — the one behaviour worth keeping from
 *  the prototype's image-slot.js. Falls back to the original on any failure. */
async function downscale(file: File): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
    if (scale === 1) return file;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d')?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((resolve) =>
      canvas.toBlob((blob) => resolve(blob ?? file), 'image/jpeg', 0.85)
    );
  } catch {
    return file;
  }
}

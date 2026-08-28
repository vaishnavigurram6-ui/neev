'use client';

// "Copy as WhatsApp message". The message is composed on the server (see
// message.ts) and arrives as a prop, so this component holds no copy and no
// figures — only the clipboard call and what to do when it is refused.
//
// The clipboard is not always available: it needs a secure context and a user
// gesture, and a browser may still deny the permission. A control that silently
// does nothing is worse than one that hands over the text, so the failure path
// reveals the message in a read-only textarea, selected, for a manual copy.
import { useId, useRef, useState } from 'react';
import Button from '@/components/ui/Button';

type Result = 'idle' | 'copied' | 'manual';

export default function CopyQuestionsButton({
  message,
  copy,
}: {
  message: string;
  copy: { cta: string; copied: string; manual: string; manualLabel: string };
}) {
  const [result, setResult] = useState<Result>('idle');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const id = useId();
  const textareaId = `${id}-message`;

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(message);
      setResult('copied');
    } catch {
      setResult('manual');
      // The textarea only exists after this render, so select it once it does.
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        textareaRef.current?.select();
      });
    }
  }

  return (
    <div className="mt-[16px]">
      <Button variant="primary" className="w-full" onClick={onCopy}>
        {copy.cta}
      </Button>

      <p role="status" className="mt-[8px] text-[11.5px] leading-[1.5] text-faint empty:hidden">
        {result === 'copied' ? copy.copied : result === 'manual' ? copy.manual : null}
      </p>

      {result === 'manual' && (
        <>
          <label htmlFor={textareaId} className="sr-only">
            {copy.manualLabel}
          </label>
          <textarea
            ref={textareaRef}
            id={textareaId}
            readOnly
            rows={8}
            value={message}
            className="mt-[8px] w-full rounded-[10px] border border-input-border bg-card p-[10px] text-[12px] leading-[1.5] text-ink"
          />
        </>
      )}
    </div>
  );
}

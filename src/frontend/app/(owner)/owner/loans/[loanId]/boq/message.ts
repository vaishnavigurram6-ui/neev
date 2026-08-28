// The share message both question CTAs compose.
//
// The mockup's rail says "Questions, not accusations — each one your contractor
// can confirm in writing", and the CTA under it is "Copy as WhatsApp message" —
// but the prototype never shows the message itself. It is assembled here from
// the question list the API returns, so the four questions the owner reads on
// screen are the four the contractor receives, word for word, including their
// figures. No number is written into this file.
//
// Plain text, not markup: WhatsApp is the intended destination and it has no
// rich clipboard format worth targeting.

import type { QuestionView } from '@/lib/types';

const LEAD = 'Questions on the BoQ before I sign';
const CLOSE = 'These are questions, not accusations — a written confirmation on each is all I need.';

export function shareMessage({
  questions,
  contractor,
  receivedLabel,
}: {
  questions: QuestionView[];
  contractor: string | null;
  /** The day the BoQ arrived, already formatted, or null when it is unknown. */
  receivedLabel: string | null;
}): string {
  const greeting = contractor ? `Hello ${contractor},` : 'Hello,';
  const lead = receivedLabel ? `${LEAD} (BoQ received ${receivedLabel}):` : `${LEAD}:`;
  // Numbered by position, not by `question.number`: the rail numbers the list
  // the same way (`GuidanceList marker="number"` counts from 1), and the two
  // must agree — the owner reads "3." on screen and points at "3." in the
  // message. `question.number` is a database column and need not be contiguous.
  const numbered = questions.map((question, index) => `${index + 1}. ${question.text}`);
  return [greeting, '', lead, '', ...numbered, '', CLOSE].join('\n');
}

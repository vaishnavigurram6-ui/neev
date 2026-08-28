// The one and only money formatter. No screen stores or emits a pre-formatted
// money string; every rupee figure on screen passes through here.

const MINUS = '−'; // U+2212 MINUS SIGN, as the designs use

/** Full Indian grouping: 3200000 -> "₹32,00,000". Negatives use a true minus. */
export function formatINR(rupees: number): string {
  if (!Number.isFinite(rupees)) return '—';
  const negative = rupees < 0;
  const digits = Math.abs(Math.round(rupees)).toString();
  let grouped: string;
  if (digits.length <= 3) {
    grouped = digits;
  } else {
    const last3 = digits.slice(-3);
    const rest = digits.slice(0, -3);
    grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3;
  }
  return `${negative ? MINUS : ''}₹${grouped}`;
}

/** Compact crore/lakh form for portfolio headlines: 25700000 -> "₹2.57 cr". */
export function formatINRCompact(rupees: number): string {
  if (!Number.isFinite(rupees)) return '—';
  const negative = rupees < 0;
  const abs = Math.abs(rupees);
  const sign = negative ? MINUS : '';
  if (abs >= 1_00_00_000) return `${sign}₹${(abs / 1_00_00_000).toFixed(2)} cr`;
  if (abs >= 1_00_000) return `${sign}₹${(abs / 1_00_000).toFixed(2)} L`;
  return formatINR(rupees);
}

/** 0.45 -> "45%". */
export function formatPct(fraction: number, dp = 0): string {
  if (!Number.isFinite(fraction)) return '—';
  return `${(fraction * 100).toFixed(dp)}%`;
}

/** Exposure ratios render to two decimals; null means undefined, never Infinity. */
export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return value.toFixed(2);
}

/** Quantities keep their natural precision: 22.5 -> "22.5", 4800 -> "4,800". */
export function formatQty(value: number): string {
  if (!Number.isFinite(value)) return '—';
  return Number.isInteger(value) ? value.toLocaleString('en-IN') : value.toString();
}

/** Signed rupee delta, for diff and change-order rows: 154000 -> "+₹1,54,000". */
export function formatDelta(rupees: number): string {
  if (!Number.isFinite(rupees)) return '—';
  return rupees > 0 ? `+${formatINR(rupees)}` : formatINR(rupees);
}

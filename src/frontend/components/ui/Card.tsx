// Card.tsx — the surface. Owner radii are 14-16px, bank 10px; that is the only
// difference, so it is a prop rather than two components.
import type { Skin } from '@/lib/tone';

export default function Card({
  as: Tag = 'div',
  skin = 'owner',
  className = '',
  children,
}: {
  as?: 'div' | 'section';
  skin?: Skin;
  className?: string;
  children: React.ReactNode;
}) {
  const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-card';
  return (
    <Tag className={`bg-card border border-line shadow-card ${radius} ${className}`}>
      {children}
    </Tag>
  );
}

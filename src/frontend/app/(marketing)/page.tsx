// Neev Landing — ported from `design_handoff_neev/Neev Landing.dc.html`.
//
// Copy, type scale and layout are the prototype's, verbatim. Three things changed
// on the way in:
//
//   * the prototype's inline `body` / `body.dark` custom properties are gone —
//     that block is now the app theme in globals.css, so the toggle works here
//     with no code of its own;
//   * the `<div onClick>` theme switch and the styled-div buttons became a real
//     <button> (kit <ThemeToggle>) and real <a>s;
//   * plan Task 14 adds the four-stage journey strip, which the prototype draws
//     on Login rather than here.
//
// No data reaches this page — it is the one screen in the product with nothing to
// load — so there are no loading / empty / error states to implement.
import type { Metadata } from 'next';
import HeroPhoto from '@/components/marketing/HeroPhoto';
import MarketingHeader from '@/components/marketing/MarketingHeader';
import Button from '@/components/ui/Button';

const HEADLINE_A = 'The home you dream of.';
const HEADLINE_B = 'Built the way you were promised.';
const STANDFIRST =
  'You don’t need to speak builder. Neev reads the contract, checks the prices, and watches your money become your home.';

// The only route in the product that is indexable or shareable, so it is the only
// one carrying Open Graph tags (spec §6.7). No `images` entry: the handoff ships
// no binary assets, and pointing og:image at a file that does not exist is worse
// than omitting it.
export const metadata: Metadata = {
  title: { absolute: 'Neev — the home you dream of, built the way you were promised' },
  description: STANDFIRST,
  robots: { index: true, follow: true },
  openGraph: {
    type: 'website',
    siteName: 'Neev',
    locale: 'en_IN',
    title: `${HEADLINE_A} ${HEADLINE_B}`,
    description: STANDFIRST,
  },
  twitter: {
    card: 'summary',
    title: `${HEADLINE_A} ${HEADLINE_B}`,
    description: STANDFIRST,
  },
};

const STEPS = [
  { n: '1', title: 'Share your contract', desc: 'A photo of it is enough.' },
  { n: '2', title: 'We read every line', desc: 'Prices checked against your neighbourhood.' },
  { n: '3', title: 'Build with open eyes', desc: 'Every payment checked against real progress.' },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <MarketingHeader />

      {/* <main> spans the hero *and* both bands: closing it after the hero would
          leave the two lists in no landmark, so anyone navigating by landmark
          would skip half the page. */}
      <main className="flex flex-1 flex-col">
        <div className="mx-auto grid w-full max-w-[1060px] flex-1 grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] content-center items-center gap-12 p-10">
          <div>
            <h1 className="font-display text-[46px] font-bold leading-[1.18] tracking-[-0.01em] text-ink">
              {HEADLINE_A}
              <br />
              <span className="text-action">{HEADLINE_B}</span>
            </h1>
            <p className="mt-4 max-w-[440px] text-pretty text-[16px] leading-[1.7] text-sub">
              {STANDFIRST}
            </p>
            <div className="mt-7 flex items-center gap-4">
              {/* Onboarding is behind the middleware, so a visitor with no
                  session is routed through /login first and returns here. */}
              <Button
                href="/owner/onboarding"
                variant="primary"
                className="px-[26px] py-[14px] font-display text-[15px] font-bold"
              >
                Check my contract — free
              </Button>
              <span className="text-[13px] font-semibold text-faint">2 minutes · no sign-up</span>
            </div>
          </div>
          <HeroPhoto
            placeholder="Family playing with their kid, new home behind"
            src="/marketing/hero-family.jpg"
            alt="A young family sitting on the floor of an empty room, the parents' hands meeting to make a roof over their daughter, under a house drawn on the wall behind them."
          />
        </div>

        {/* The page's one supporting statement, and the only thing under the
            hero. It used to sit above a second numbered band — the four-stage
            journey strip — which said the same thing from the product's side:
            seven items, two sequences, one counting from 1 and the other from
            0. The journey strip is on Login and Onboarding, so a visitor who
            acts meets it on the very next screen; here it was the accessory to
            take off. What stays answers the only question a visitor with a
            contract in their hand is asking, which is what to do with it. */}
        <div className="border-t border-line">
          <ol
            aria-label="How Neev works, in three steps"
            className="mx-auto grid max-w-[1060px] grid-cols-3 gap-10 px-10 py-11"
          >
            {STEPS.map((step) => (
              <li key={step.n} className="flex items-baseline gap-[14px]">
                <span className="flex-none font-display text-[19px] font-bold text-action">
                  {step.n}
                </span>
                <div>
                  <div className="text-[15px] font-bold leading-[1.35] text-ink">{step.title}</div>
                  <div className="mt-[5px] max-w-[30ch] text-[13px] leading-[1.6] text-sub">
                    {step.desc}
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </div>

      </main>

      <footer className="px-10 pb-5 pt-4 text-center text-[11.5px] text-faint">
        Neev · नींव — the foundation · English · हिंदी · తెలుగు
      </footer>
    </div>
  );
}

import type { Metadata } from 'next';
import { Baloo_2, Instrument_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';

const baloo = Baloo_2({
  subsets: ['latin', 'devanagari'],
  weight: ['500', '600', '700'],
  variable: '--font-baloo',
  display: 'swap',
});

const instrument = Instrument_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-instrument',
  display: 'swap',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-jetbrains',
  display: 'swap',
});

export const metadata: Metadata = {
  title: { default: 'Neev', template: '%s · Neev' },
  description:
    'Neev protects self-construction home loans on both sides of the table — flagging inflated rates and missing scope before you sign, then verifying every payment against real site progress.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${baloo.variable} ${instrument.variable} ${jetbrains.variable}`}
    >
      <head>
        {/* Applies the saved theme before first paint so the page never flashes
            the wrong palette. Falls back to the OS preference.

            The storage read has its own try/catch: where site data is blocked,
            getItem throws, and a single try around the whole thing would swallow
            it before matchMedia ran — leaving data-theme unset and pinning those
            viewers to the light palette however their OS is set. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){var t=null;try{t=localStorage.getItem('neev-theme');}catch(e){}if(t!=='dark'&&t!=='light'){try{t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}catch(e){t='light';}}try{document.documentElement.setAttribute('data-theme',t);}catch(e){}})();`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}

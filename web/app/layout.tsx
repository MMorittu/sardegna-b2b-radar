import type { Metadata } from 'next';
import { Inter, Space_Grotesk } from 'next/font/google';
import { ReactGrabDev } from '@/components/layout/ReactGrabDev';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-space',
});

export const metadata: Metadata = {
  title: 'Sardegna B2B Radar — Public Procurement & Regional Grant Intelligence',
  description: 'Industrial Procurement Intelligence & Tender Monitoring Dashboard for Sardinia',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it" className={`${inter.variable} ${spaceGrotesk.variable}`}>
      <body className="min-h-screen font-sans bg-brand-surface text-brand-ink antialiased">
        {children}
        {process.env.NODE_ENV === 'development' && <ReactGrabDev />}
      </body>
    </html>
  );
}

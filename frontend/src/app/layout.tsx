import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'FirstPR — Your first pull request starts here',
  description: 'Find approachable open source issues and plan your first pull request.',
  icons: { icon: '/icon.png', apple: '/icon.png' },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}

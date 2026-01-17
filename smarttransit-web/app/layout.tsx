// app/layout.tsx
import './globals.css';
import { Inter } from 'next/font/google';
import { SupabaseProvider } from '@/lib/supabase-provider';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'SmartTransit',
  description: 'Real-time transit system',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-zinc-50 min-h-screen`}>
        <SupabaseProvider>{children}</SupabaseProvider>
      </body>
    </html>
  );
}

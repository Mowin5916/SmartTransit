'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';

export default function Header({ email }: { email?: string }) {
  const router = useRouter();
  const [loading, setLoading] = React.useState(false);

  async function handleSignOut() {
    setLoading(true);
    try {
      await supabase.auth.signOut();
    } catch (err) {
      console.error('signOut error', err);
    } finally {
      setLoading(false);
      router.push('/login');
    }
  }

  return (
    <header className="w-full flex items-center justify-between bg-white p-4 shadow-sm rounded mb-4">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-indigo-100 text-indigo-700 rounded-full flex items-center justify-center font-bold text-lg">
          {email ? email[0].toUpperCase() : 'U'}
        </div>
        <div>
          <div className="text-lg font-semibold text-indigo-600">SmartTransit</div>
          {email && <div className="text-sm text-gray-600">Signed in as {email}</div>}
        </div>
      </div>

      <div>
        <button
          onClick={handleSignOut}
          disabled={loading}
          className="px-3 py-1 rounded-md bg-red-500 text-white hover:bg-red-600 disabled:opacity-60"
        >
          {loading ? 'Signing out…' : 'Sign out'}
        </button>
      </div>
    </header>
  );
}

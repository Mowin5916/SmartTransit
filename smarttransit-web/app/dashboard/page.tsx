// app/dashboard/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function init() {
      try {
        const { data: sessionData } = await supabase.auth.getSession();
        const session = sessionData.session;
        if (!session) {
          router.push('/login');
          return;
        }

        const { data: profile, error } = await supabase
          .from('profiles')
          .select('id, full_name, role')
          .eq('id', session.user.id)
          .limit(1)
          .single();

        if (error) {
          console.warn('Profile fetch error:', error.message || error);
          // If profile missing or RLS blocked, fallback to a default page or login
          // Here we send the user to passenger as a safe default.
          router.push('/passenger');
          return;
        }

        if (!mounted) return;

        const role = profile?.role;
        if (!role) {
          // If role is unexpectedly empty, send to a sensible default (passenger)
          router.push('/passenger');
          return;
        }

        // Use template string to build the correct path
        router.push(`/${role}`);
      } catch (err) {
        console.error('Dashboard init error', err);
        // On unexpected error, fallback to login
        router.push('/login');
      } finally {
        if (mounted) setLoading(false);
      }
    }

    init();

    return () => {
      mounted = false;
    };
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">Loading your dashboard…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6">
      <div className="bg-white p-6 rounded shadow">
        <h2 className="text-xl font-semibold">Dashboard</h2>
        <p className="text-sm text-gray-600">Redirecting based on your role…</p>
      </div>
    </div>
  );
}

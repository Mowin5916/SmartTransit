// app/login/page.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import VideoBackground from '@/app/components/VideoBackground';

/**
 * Classic Login Page for SmartTransit
 * - No Supabase-hosted widget
 * - Clean email/password form
 * - Decorative bus SVG header with subtle animation
 * - Accessible form (labels, aria, keyboard)
 * - Shows loading and friendly error messages
 */

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Redirect if already signed in
  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      if (data.session) router.push('/dashboard');
    });

    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        router.push('/dashboard');
      }
    });

    return () => {
      try {
        listener?.subscription?.unsubscribe();
      } catch {}
      mounted = false;
    };
  }, [router]);

  function validate() {
    if (!email.trim()) {
      setError('Please enter your email address.');
      return false;
    }
    if (!/^\S+@\S+\.\S+$/.test(email)) {
      setError('Please enter a valid email address.');
      return false;
    }
    if (!password) {
      setError('Please enter your password.');
      return false;
    }
    return true;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!validate()) return;

    try {
      setLoading(true);
      const { error: signErr } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (signErr) {
        if (signErr.message?.includes('invalid login credentials')) {
          setError('Invalid email or password.');
        } else {
          setError(signErr.message || 'Failed to sign in.');
        }
        setLoading(false);
        return;
      }

      setLoading(false);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err?.message || 'Unexpected error during sign in.');
      setLoading(false);
    }
  }

  return (
    <>
      <VideoBackground />

      <div className="relative z-10 min-h-screen flex items-center justify-center p-8">
        <div className="w-full max-w-lg">
          <div className="bg-zinc-900/90 rounded-2xl p-10 md:p-12 ring-1 ring-white/10 shadow-2xl">
            {/* Header */}
            <div className="flex items-center gap-6 mb-8">
              <div
                className="w-20 h-20 flex items-center justify-center rounded-xl bg-indigo-600/10"
                aria-hidden
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 64 64"
                  width="60"
                  height="60"
                  className="animate-bounce-slow"
                  role="img"
                >
                  <rect x="6" y="10" width="52" height="32" rx="4" fill="#6d28d9" />
                  <rect x="10" y="14" width="20" height="12" rx="1" fill="#ffffff" opacity="0.95" />
                  <rect x="34" y="14" width="18" height="12" rx="1" fill="#ffffff" opacity="0.6" />
                  <circle cx="18" cy="46" r="5" fill="#111827" />
                  <circle cx="46" cy="46" r="5" fill="#111827" />
                </svg>
              </div>

              <div>
                <h1 className="text-3xl font-bold text-white">SmartTransit</h1>
                <p className="text-base text-zinc-300 mt-1">
                  Real-time transit for passengers & drivers
                </p>
              </div>
            </div>

            <main>
              <h2 className="text-xl font-semibold text-white mb-5">
                Sign in to your account
              </h2>

              <form onSubmit={handleSubmit} className="space-y-6">

                {/* Email */}
                <div>
                  <label htmlFor="email" className="block text-base font-medium text-zinc-200">
                    Email address
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="mt-2 block w-full rounded-md bg-white/5 border border-white/10 text-white text-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="you@example.com"
                  />
                </div>

                {/* Password */}
                <div>
                  <label htmlFor="password" className="block text-base font-medium text-zinc-200">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="mt-2 block w-full rounded-md bg-white/5 border border-white/10 text-white text-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Your password"
                  />
                </div>

                <div className="flex items-center justify-between text-base">
                  <a href="/signup" className="text-indigo-400 hover:text-indigo-300">
                    Create an account
                  </a>
                  <span className="text-zinc-300 cursor-pointer hover:underline">
                    Forgot password?
                  </span>
                </div>

                {error && (
                  <div className="text-base text-amber-400 bg-amber-900/20 p-3 rounded-lg">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-indigo-600 hover:bg-indigo-500 px-5 py-3 text-lg text-white font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-400 disabled:opacity-60"
                >
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
              </form>

              <p className="text-sm text-zinc-400 mt-6">
                Sign in to continue using SmartTransit.
              </p>
            </main>
          </div>

          <div className="mt-8 text-center text-base text-zinc-400">
            🚍 Live ETAs • Driver tips • Planner dashboard
          </div>

          <style jsx>{`
            .animate-bounce-slow {
              animation: bounce 2.6s infinite;
            }
            @keyframes bounce {
              0%, 100% { transform: translateY(0); }
              50% { transform: translateY(-8px); }
            }
          `}</style>
        </div>
      </div>
    </>
  );
}
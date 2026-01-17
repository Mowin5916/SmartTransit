// app/signup/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import VideoBackground from '@/app/components/VideoBackground';

const SignupSchema = z.object({
  full_name: z.string().min(2, 'Enter your name'),
  email: z.string().email('Invalid email'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  role: z.enum(['passenger', 'driver', 'conductor', 'planner']),
});

type SignupValues = z.infer<typeof SignupSchema>;

export default function SignupPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SignupValues>({
    resolver: zodResolver(SignupSchema),
    defaultValues: { role: 'passenger' },
  });

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
      } catch (e) {}
      mounted = false;
    };
  }, [router]);

  async function onSubmit(values: SignupValues) {
    setLoading(true);
    setNotice(null);

    try {
      try {
        localStorage.setItem('pending_role', values.role);
        localStorage.setItem('pending_name', values.full_name);
      } catch (e) {}

      const { data, error } = await supabase.auth.signUp({
        email: values.email,
        password: values.password,
      });

      if (error) {
        setNotice(error.message);
        setLoading(false);
        return;
      }

      const user = (data as any).user ?? null;

      if (user) {
        const { error: pErr } = await supabase.from('profiles').upsert({
          id: user.id,
          full_name: values.full_name,
          role: values.role,
        });

        if (pErr) {
          setNotice('Signed up but failed to create profile: ' + pErr.message);
          setLoading(false);
          return;
        }

        setLoading(false);
        router.push('/dashboard');
        return;
      }

      setNotice(
        'Signup initiated. Check your email to confirm. After confirming, sign in and the role will be applied.'
      );
      setLoading(false);
    } catch (err: any) {
      setNotice(err?.message || 'Unexpected error during signup.');
      setLoading(false);
    }
  }

  return (
    <>
      <VideoBackground />

      <div className="relative z-10 min-h-screen flex items-center justify-center p-8">
        <div className="w-full max-w-lg">

          <div className="bg-zinc-900/90 rounded-2xl p-10 md:p-12 ring-1 ring-white/10 shadow-2xl">
            {/* Header with bus SVG */}
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
                  <rect x="6" y="10" width="54" height="32" rx="4" fill="#6d28d9" />
                  <rect x="10" y="14" width="20" height="12" rx="1" fill="#ffffff" opacity="0.95" />
                  <rect x="34" y="14" width="18" height="12" rx="1" fill="#ffffff" opacity="0.6" />
                  <circle cx="18" cy="46" r="5" fill="#111827" />
                  <circle cx="46" cy="46" r="5" fill="#111827" />
                  <rect x="8" y="26" width="48" height="5" fill="#3f3f46" opacity="0.12" />
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
              <h2 className="text-xl font-semibold text-white mb-4">
                Create an account
              </h2>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* FULL NAME */}
                <div>
                  <label htmlFor="full_name" className="block text-base font-medium text-zinc-200">
                    Full name
                  </label>
                  <input
                    id="full_name"
                    {...register('full_name')}
                    className="mt-2 block w-full rounded-md bg-white/5 border border-white/10 text-white text-lg px-4 py-3"
                    placeholder="Your full name"
                  />
                  {errors.full_name && (
                    <div className="text-sm text-red-500 mt-1">
                      {errors.full_name.message}
                    </div>
                  )}
                </div>

                {/* EMAIL */}
                <div>
                  <label htmlFor="email" className="block text-base font-medium text-zinc-200">
                    Email address
                  </label>
                  <input
                    id="email"
                    type="email"
                    {...register('email')}
                    className="mt-2 block w-full rounded-md bg-white/5 border border-white/10 text-white text-lg px-4 py-3"
                    placeholder="you@example.com"
                  />
                  {errors.email && (
                    <div className="text-sm text-red-500 mt-1">
                      {errors.email.message}
                    </div>
                  )}
                </div>

                {/* PASSWORD */}
                <div>
                  <label htmlFor="password" className="block text-base font-medium text-zinc-200">
                    Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    {...register('password')}
                    className="mt-2 block w-full rounded-md bg-white/5 border border-white/10 text-white text-lg px-4 py-3"
                    placeholder="Choose a secure password"
                  />
                  {errors.password && (
                    <div className="text-sm text-red-500 mt-1">
                      {errors.password.message}
                    </div>
                  )}
                </div>

                {/* ROLES */}
                <div>
                  <label className="block text-base font-medium mb-2 text-zinc-200">
                    Role
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {(['passenger', 'driver', 'conductor', 'planner'] as const).map((r) => (
                      <label
                        key={r}
                        className="flex items-center gap-3 p-3 rounded-lg border border-white/10 bg-white/5"
                      >
                        <input
                          {...register('role')}
                          type="radio"
                          value={r}
                          className="h-5 w-5"
                          defaultChecked={r === 'passenger'}
                        />
                        <span className="capitalize text-lg text-zinc-200">
                          {r}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                {notice && (
                  <div className="text-base text-amber-400 bg-amber-900/20 p-3 rounded-lg">
                    {notice}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg bg-indigo-600 px-5 py-3 text-lg text-white font-semibold disabled:opacity-60"
                >
                  {loading ? 'Creating account…' : 'Create account'}
                </button>
              </form>
            </main>
          </div>

          <div className="mt-8 text-center text-base text-zinc-400">
            🚍 Live ETAs • Driver tips • Planner dashboard
          </div>

          <style jsx>{`
            .animate-bounce-slow {
              animation: bounce 2.8s infinite;
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

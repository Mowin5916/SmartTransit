'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { getAssignmentForUser, getRoutes, getProfileById, getWorkHistory, UserProfile } from '@/lib/api';
import PassengerCounter from '@/app/components/PassengerCounter';

export default function DriverPage() {
  const router = useRouter();
  const [session, setSession] = useState<any>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  
  // Dashboard Data
  const [assignment, setAssignment] = useState<any | null>(null);
  const [route, setRoute] = useState<any | null>(null);
  const [conductor, setConductor] = useState<UserProfile | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // --- CONFIGURATION ---
  const BUS_ID = '8b917f9c-83c0-49dc-b92a-0877dc87402c'; 

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push('/login'); return; }
      
      if (mounted) setSession(session);
      const userId = session.user.id;

      // Fetch Profile & History
      const myProfile = await getProfileById(userId);
      const hist = await getWorkHistory(userId);
      
      if (mounted) {
        setProfile(myProfile);
        setHistory(hist);
      }

      // Fetch Assignment
      const ass = await getAssignmentForUser(userId).catch(() => null);
      
      if (mounted) {
        setAssignment(ass);

        if (ass) {
          // --- IF ASSIGNED ---
          
          // 1. Find Route (With String Cast Fix)
          if (ass.route_id) {
            const routes = await getRoutes();
            const r = routes.find((x: any) => String(x.id) === String(ass.route_id));
            setRoute(r || null);
          } else {
            setRoute(null);
          }

          // 2. Find Conductor
          if (ass.conductor_id) {
            const cond = await getProfileById(ass.conductor_id);
            setConductor(cond);
          } else {
            setConductor(null);
          }

        } else {
          // --- IF UNASSIGNED (Clear State) ---
          setRoute(null);
          setConductor(null);
        }

        setLoading(false);
      }
    }

    loadData();
    return () => { mounted = false; };
  }, [router]);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  const getExperienceDays = () => {
    if (!profile?.created_at) return 0;
    const start = new Date(profile.created_at);
    return Math.floor((new Date().getTime() - start.getTime()) / (1000 * 3600 * 24));
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-500">Loading...</div>;

  return (
  <div className="min-h-screen bg-[#0a0a0f] text-white p-4 md:p-6 font-sans">

    {/* HEADER */}
    <header className="max-w-4xl mx-auto bg-zinc-900/80 backdrop-blur p-4 rounded-2xl border border-white/10 mb-6 shadow-2xl flex justify-between items-center">
      <div className="flex items-center gap-4">
        <div className="h-12 w-12 bg-indigo-600 text-white rounded-xl flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-500/30">
          {profile?.full_name ? profile.full_name[0].toUpperCase() : 'D'}
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight">Driver Portal</h1>
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-medium border border-emerald-500/30">
              Verified Driver
            </span>
            <span>• Exp: {getExperienceDays()} Days</span>
          </div>
        </div>
      </div>
      <button
        onClick={handleLogout}
        className="px-4 py-2 text-xs font-bold text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg transition-all"
      >
        Sign Out
      </button>
    </header>

    <main className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">

      {/* LEFT COLUMN */}
      <div className="lg:col-span-2 space-y-6">

        <div className="bg-zinc-900/70 p-6 rounded-2xl shadow-xl border border-indigo-500/20 relative overflow-hidden">
          <div className="relative z-10">
            <h2 className="text-sm font-bold text-zinc-400 uppercase tracking-wider mb-4">
              Current Route Assignment
            </h2>

            {!assignment ? (
              <div className="text-center py-8 text-zinc-500 border-2 border-dashed border-white/10 rounded-xl">
                <p>No active route assigned.</p>
              </div>
            ) : (
              <>
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <div className="text-4xl font-black text-white">
                      {route?.id || assignment.route_id}
                    </div>
                    <div className="text-lg text-zinc-400 font-medium">
                      {route?.name || 'Loading details...'}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-zinc-500 mb-1">Bus Number</div>
                    <div className="text-lg font-bold font-mono bg-black/40 px-3 py-1 rounded-lg border border-white/10">
                      KA-01-F-1234
                    </div>
                  </div>
                </div>

                <div className="bg-indigo-900/20 rounded-xl p-4 flex items-center gap-4 border border-indigo-500/20 mb-6">
                  <div className="h-10 w-10 rounded-full bg-indigo-600/30 flex items-center justify-center text-indigo-300 font-bold">
                    {conductor?.full_name ? conductor.full_name[0] : 'C'}
                  </div>
                  <div>
                    <p className="text-xs text-indigo-400 font-bold uppercase">
                      Assigned Conductor
                    </p>
                    <p className="text-white font-bold">
                      {conductor?.full_name || 'Pending Assignment'}
                    </p>
                    {conductor?.phone && (
                      <p className="text-xs text-zinc-400">📞 {conductor.phone}</p>
                    )}
                  </div>
                </div>

                <div className="border-t border-white/10 pt-6">
                  <PassengerCounter busId={BUS_ID} />
                </div>
              </>
            )}
          </div>
        </div>

        {route && route.stops && (
          <div className="bg-zinc-900/70 p-6 rounded-2xl shadow-xl border border-white/10">
            <h3 className="text-lg font-bold text-white mb-4">
              Stops Sequence
            </h3>
            <div className="flex flex-wrap gap-2">
              {Array.isArray(route?.stops) ? route.stops.map((stop: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center text-sm text-zinc-300 bg-black/40 px-3 py-2 rounded-lg border border-white/10"
                >
                  <span className="w-5 h-5 flex items-center justify-center bg-indigo-600/40 rounded-full text-xs font-bold mr-2 text-indigo-300">
                    {i + 1}
                  </span>
                  {stop}
                </div>
              )) : null}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN */}
      <div className="space-y-6">

        <div className="bg-zinc-900/70 p-5 rounded-2xl shadow-xl border border-white/10">
          <h3 className="font-bold text-white mb-4">My Stats</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-indigo-900/20 p-3 rounded-xl text-center border border-indigo-500/20">
              <div className="text-2xl font-black text-indigo-400">
                {getExperienceDays()}
              </div>
              <div className="text-xs text-indigo-300 font-medium">
                Days Active
              </div>
            </div>
            <div className="bg-emerald-900/20 p-3 rounded-xl text-center border border-emerald-500/20">
              <div className="text-2xl font-black text-emerald-400">
                {history.length}
              </div>
              <div className="text-xs text-emerald-300 font-medium">
                Trips Completed
              </div>
            </div>
          </div>
        </div>

        <div className="bg-zinc-900/70 p-5 rounded-2xl shadow-xl border border-white/10">
          <h3 className="font-bold text-white mb-4">
            Previous Assignments
          </h3>
          <div className="space-y-4">
            {history.length === 0 ? (
              <p className="text-sm text-zinc-500">No history found.</p>
            ) : (
              history.map((job, idx) => (
                <div
                  key={idx}
                  className="flex justify-between pb-3 border-b border-white/5 last:border-0"
                >
                  <div>
                    <p className="text-sm font-bold text-white">
                      {job.route_name}
                    </p>
                    <p className="text-xs text-zinc-500">{job.date}</p>
                  </div>
                  <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded-full h-fit border border-emerald-500/30">
                    {job.hours}h
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </main>
  </div>
);
}
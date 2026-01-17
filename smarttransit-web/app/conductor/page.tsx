'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { reportIncident, getAssignmentForUser, getRoutes, getProfileById, getWorkHistory, UserProfile } from '@/lib/api';
import PassengerCounter from '@/app/components/PassengerCounter';

export default function ConductorPage() {
  const router = useRouter();
  
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [assignment, setAssignment] = useState<any | null>(null);
  const [assignedRoute, setAssignedRoute] = useState<any | null>(null);
  const [driver, setDriver] = useState<UserProfile | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Incident Form
  const [selectedRouteId, setSelectedRouteId] = useState('');
  const [incidentType, setIncidentType] = useState('Breakdown');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [allRoutes, setAllRoutes] = useState<any[]>([]); // For dropdown

  const DEMO_BUS_ID = '8b917f9c-83c0-49dc-b92a-0877dc87402c';

  useEffect(() => {
    let mounted = true;

    async function init() {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) { router.push('/login'); return; }

      const userId = session.user.id;
      const myProfile = await getProfileById(userId);
      const hist = await getWorkHistory(userId);
      const routesList = await getRoutes(); // Load all routes for dropdown
      
      if (mounted) {
        setProfile(myProfile);
        setHistory(hist);
        setAllRoutes(routesList);
      }

      // Fetch Assignment
      const ass = await getAssignmentForUser(userId).catch(() => null);
      
      if (mounted) {
        setAssignment(ass);
        
        if (ass) {
          // --- IF ASSIGNED ---
          
          // 1. Set Route
          if (ass.route_id) {
             const r = routesList.find((x: any) => String(x.id) === String(ass.route_id));
             setAssignedRoute(r);
             setSelectedRouteId(String(ass.route_id)); // Auto-select in dropdown
          } else {
             setAssignedRoute(null);
          }

          // 2. Set Driver
          if (ass.driver_id) {
             const d = await getProfileById(ass.driver_id);
             setDriver(d);
          } else {
             setDriver(null);
          }
        } else {
          // --- IF UNASSIGNED (Clear State) ---
          setAssignedRoute(null);
          setDriver(null);
          setSelectedRouteId('');
        }
        
        setLoading(false);
      }
    }
    init();
    return () => { mounted = false; };
  }, [router]);

  const handleReport = async () => {
    if (!selectedRouteId) { alert('Select a route'); return; }
    setSubmitting(true);
    try {
      await reportIncident({
        route_id: selectedRouteId,
        type: incidentType,
        message: description || 'No additional details.'
      });
      alert('🚨 Incident Reported!');
      setDescription('');
    } catch (err: any) {
      alert('Error: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  const getExperienceDays = () => {
    if (!profile?.created_at) return 0;
    return Math.floor((new Date().getTime() - new Date(profile.created_at).getTime()) / (1000 * 3600 * 24));
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-zinc-500">Loading Dashboard...</div>;

  return (
  <div className="min-h-screen bg-[#0a0a0f] text-white p-4 md:p-6 font-sans">

    {/* Header */}
    <header className="max-w-4xl mx-auto bg-zinc-900/80 backdrop-blur p-4 rounded-2xl border border-white/10 mb-6 flex justify-between items-center shadow-2xl">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 bg-red-600/30 text-red-400 rounded-xl flex items-center justify-center font-bold text-lg shadow-lg shadow-red-500/30">
          {profile?.full_name ? profile.full_name[0].toUpperCase() : 'C'}
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight">Conductor Portal</h1>
          <p className="text-xs text-zinc-400">
            Exp: {getExperienceDays()} Days
          </p>
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

      {/* LEFT: LIVE OPERATIONS */}
      <div className="lg:col-span-2 space-y-6">

        <div className="bg-zinc-900/70 rounded-2xl shadow-xl border border-white/10 p-5">
          <h2 className="text-xs font-bold text-zinc-400 uppercase tracking-wide mb-3">
            Today's Duty
          </h2>

          {assignedRoute ? (
            <div className="flex items-center justify-between bg-black/40 p-4 rounded-xl border border-white/10 mb-4">
              <div>
                <div className="text-xl font-bold text-white">
                  {assignedRoute.id}: {assignedRoute.name}
                </div>
                <div className="text-xs text-emerald-400 font-bold">
                  Active Shift
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-zinc-500 uppercase font-bold mb-1">
                  Driver
                </div>
                <div className="font-medium text-zinc-200">
                  {driver?.full_name || 'Unassigned'}
                </div>
                <div className="text-xs text-zinc-400">
                  {driver?.phone}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-zinc-500 italic mb-4 border-2 border-dashed border-white/10 rounded-xl p-4 text-center">
              No specific route assigned currently.
            </p>
          )}

          <div className="border-t border-white/10 pt-4">
            <h3 className="text-sm font-bold text-zinc-300 mb-2">
              Live Occupancy
            </h3>
            <PassengerCounter busId={DEMO_BUS_ID} />
          </div>
        </div>

        {/* EMERGENCY REPORTING */}
        <div className="bg-zinc-900/80 rounded-2xl shadow-2xl border border-red-500/20 overflow-hidden">
          <div className="bg-red-600/20 border-b border-red-500/30 p-3 text-red-400 flex items-center gap-3">
            <h2 className="text-lg font-bold tracking-tight">
              Emergency Reporting
            </h2>
          </div>

          <div className="p-5 space-y-4">
            <div>
              <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">
                Affected Route
              </label>
              <select
                value={selectedRouteId}
                onChange={e => setSelectedRouteId(e.target.value)}
                className="w-full p-2 bg-black border border-white/10 rounded-lg outline-none focus:ring-2 focus:ring-red-500 text-sm text-white"
              >
                <option value="">-- Select Route --</option>
                {allRoutes.map(r => (
                  <option key={r.id} value={r.id}>
                    {r.id}: {r.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">
                Incident Type
              </label>
              <div className="grid grid-cols-2 gap-2">
                {['Breakdown', 'Accident', 'Heavy Traffic', 'Medical Emergency'].map(type => (
                  <button
                    key={type}
                    onClick={() => setIncidentType(type)}
                    className={`p-2 rounded-lg border text-xs font-bold transition-all
                      ${incidentType === type
                        ? 'bg-red-500/20 border-red-500 text-red-400'
                        : 'bg-black/40 border-white/10 text-zinc-400 hover:bg-white/5'
                      }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Details..."
              className="w-full p-3 bg-black border border-white/10 rounded-xl h-20 resize-none outline-none focus:ring-2 focus:ring-red-500 text-sm text-white"
            />

            <button
              onClick={handleReport}
              disabled={submitting}
              className="w-full bg-red-600 hover:bg-red-500 text-white font-bold py-3 rounded-xl shadow-lg shadow-red-500/30 transition-all disabled:opacity-50"
            >
              {submitting ? 'Sending...' : 'REPORT INCIDENT'}
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT: HISTORY */}
      <div className="bg-zinc-900/70 p-5 rounded-2xl shadow-xl border border-white/10 h-full">
        <h3 className="font-bold text-white mb-4">
          Shift History
        </h3>
        <div className="space-y-4">
          {history.length === 0 ? (
            <p className="text-sm text-zinc-500">
              No past shifts found.
            </p>
          ) : (
            history.map((job, idx) => (
              <div
                key={idx}
                className="pb-3 border-b border-white/5 last:border-0"
              >
                <div className="flex justify-between items-start">
                  <p className="text-sm font-bold text-white">
                    {job.route_name}
                  </p>
                  <span className="text-xs text-zinc-500">
                    {job.date}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] uppercase font-bold bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">
                    {job.status}
                  </span>
                  <span className="text-[10px] text-zinc-500">
                    {job.hours} hrs
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </main>
  </div>
);
}
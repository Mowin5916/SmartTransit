'use client';

import { useEffect, useState, useRef } from 'react';
import { supabase } from '@/lib/supabase';
import { useRouter } from 'next/navigation';
import { BANGALORE_ROUTES } from '@/lib/constants';
import { submitReview, fetchCombinedPrediction } from '@/lib/api';

export default function PassengerPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Selection State
  const [selectedRouteId, setSelectedRouteId] = useState('');
  const [selectedStop, setSelectedStop] = useState('');
  const [signaling, setSignaling] = useState(false);
  const [lastSignal, setLastSignal] = useState<{ route: string; stop: string } | null>(null);
  
  // Review State
  const [rating, setRating] = useState(5);
  const [reviewText, setReviewText] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [greenPoints, setGreenPoints] = useState(150);

  // Voice Assistant State
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [assistantReply, setAssistantReply] = useState('');
  const [processingVoice, setProcessingVoice] = useState(false);
  
  const recognitionRef = useRef<any>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);

  useEffect(() => {
    let mounted = true;
    async function fetchProfile() {
      const { data: sessionData } = await supabase.auth.getSession();
      if (!sessionData.session) { router.push('/login'); return; }
      const { data } = await supabase.from('profiles').select('*').eq('id', sessionData.session.user.id).single();
      if (mounted) setProfile(data);
      setLoading(false);
    }
    fetchProfile();

    if (typeof window !== 'undefined') {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.continuous = false;
            recognitionRef.current.lang = 'en-US';
            recognitionRef.current.onresult = handleVoiceResult;
            recognitionRef.current.onend = () => setIsListening(false);
        }
        synthRef.current = window.speechSynthesis;
    }
    return () => { mounted = false; };
  }, [router]);

  const activeRoute = BANGALORE_ROUTES.find(r => r.id === selectedRouteId);

  // --- AUTH LOGIC ---
  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push('/login');
  };

  // --- VOICE LOGIC ---
  const handleVoiceResult = (event: any) => {
      const text = event.results[0][0].transcript;
      setTranscript(text);
      processQuery(text);
  };

  const startListening = () => {
      if (!recognitionRef.current) return alert("Browser not supported.");
      setIsListening(true);
      setAssistantReply('');
      recognitionRef.current.start();
  };

  const speak = (text: string) => {
      if (synthRef.current) {
          synthRef.current.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          synthRef.current.speak(utterance);
      }
  };

  const processQuery = async (query: string) => {
      setProcessingVoice(true);
      const lower = query.toLowerCase();
      let reply = "I didn't catch that. Try asking about a route like 'R1'.";

      const routeMatch = BANGALORE_ROUTES.find(r => 
          lower.includes(r.id.toLowerCase()) || 
          lower.includes(r.id.replace('R', 'r ').toLowerCase()) || 
          lower.includes(r.name.toLowerCase())
      );

      if (routeMatch) {
          const currentHour = new Date().getHours();
          const routeNum = parseInt(routeMatch.id.replace('R', '')) || 22;
          const destName = routeMatch.name.split('→')[1]?.trim() || 'Destination';

          try {
              const aiData = await fetchCombinedPrediction({
                  time_slot: 2,
                  live_congestion: 50, 
                  usual_congestion: 45,
                  route_features: { Route_ID: routeNum, Hour: currentHour, Weather: 1, Holiday: 0 }
              });

              const eta = Math.ceil(aiData.delay_min_per_10km) + 5;
              const crowdMsg = aiData.overcrowding_risk === 'High' ? "It is currently crowded." : "Seats are available.";
              reply = `The next bus for ${routeMatch.id} to ${destName} arrives in ${eta} minutes. ${crowdMsg}`;
              setSelectedRouteId(routeMatch.id);
          } catch (error) {
              reply = `I found route ${routeMatch.id}, but cannot connect to the prediction server.`;
          }
      } else if (lower.includes("hello")) {
          reply = "Hello! I am your Transit Assistant.";
      }

      setProcessingVoice(false);
      setAssistantReply(reply);
      speak(reply);
  };

  // --- ACTIONS ---
  const handleImComing = async () => {
    if (!selectedRouteId || !selectedStop) return;
    setSignaling(true);
    const { error } = await supabase.from('passenger_signals').insert({ route_id: selectedRouteId, stop_name: selectedStop });
    if (error) alert(error.message);
    else {
      setLastSignal({ route: activeRoute?.name || selectedRouteId, stop: selectedStop });
      setSelectedStop('');
    }
    setSignaling(false);
  };

  const handleReview = async () => {
    if (!selectedRouteId) return alert("Select a route first");
    setReviewing(true);
    try {
      await submitReview({ route_id: selectedRouteId, rating, comment: reviewText });
      setGreenPoints(prev => prev + 10);
      setReviewText(''); setRating(5);
      alert("Review Submitted! +10 Points");
    } catch (e) { alert('Error submitting'); }
    finally { setReviewing(false); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-[#050508] text-zinc-500 font-medium font-mono uppercase tracking-widest animate-pulse">Loading Interface...</div>;

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-[#050508] text-white font-sans selection:bg-indigo-500/30 pb-12">
      
      {/* --- BACKGROUND ANIMATION LAYER --- */}
      <div className="absolute inset-0 z-0 fixed">
          <div className="absolute top-[-50%] left-[-50%] w-[200%] h-[200%] animate-gradient opacity-30 bg-gradient-to-br from-indigo-900/40 via-purple-900/10 to-emerald-900/20 blur-3xl"></div>
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150"></div>
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        
        {/* --- HEADER --- */}
        <header className="flex justify-between items-center bg-black/40 backdrop-blur-md px-6 py-4 rounded-2xl border border-white/5 shadow-2xl mb-8">
           <div className="flex items-center gap-4">
              <div className="h-10 w-10 bg-gradient-to-br from-indigo-600 to-violet-600 rounded-lg flex items-center justify-center font-bold text-xl shadow-lg shadow-indigo-500/30 ring-1 ring-white/20">ST</div>
              <div>
                 <h1 className="text-lg font-bold tracking-tight text-white/90">Passenger <span className="text-indigo-400">Portal</span></h1>
                 <p className="text-zinc-500 text-[10px] font-mono uppercase tracking-wider">{profile?.email}</p>
              </div>
           </div>
           
           <div className="flex items-center gap-6">
               <div className="hidden md:block">
                   <span className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-bold uppercase tracking-wider animate-pulse">
                       ● System Online
                   </span>
               </div>
               
               {/* --- SIGN OUT BUTTON --- */}
               <button 
                  onClick={handleSignOut}
                  className="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-4 py-2 rounded-lg text-xs font-bold border border-red-500/20 transition-all flex items-center gap-2 backdrop-blur-sm"
               >
                  LOGOUT
               </button>
           </div>
        </header>

        {/* --- BENTO GRID LAYOUT --- */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-[minmax(180px,auto)]">
            
            {/* 1. HERO: VOICE ASSISTANT (Spans 2 cols) */}
            <div className={`col-span-1 md:col-span-2 relative overflow-hidden rounded-3xl p-8 border border-white/10 shadow-2xl transition-all duration-500 group ${isListening ? 'bg-indigo-900/40 ring-1 ring-indigo-500/50' : 'bg-black/40 backdrop-blur-md'}`}>
                {/* Background Glows */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl -mr-16 -mt-16 pointer-events-none"></div>
                <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-500/10 rounded-full blur-2xl -ml-10 -mb-10 pointer-events-none"></div>

                <div className="relative z-10 flex flex-col h-full justify-between">
                    <div className="flex justify-between items-start">
                        <div>
                            <div className="inline-flex items-center gap-2 bg-white/5 border border-white/10 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest text-indigo-300 mb-3">
                                <span className={`w-1.5 h-1.5 rounded-full ${isListening ? 'bg-red-500 animate-ping' : 'bg-emerald-500'}`}></span> 
                                {isListening ? 'Mic Active' : 'AI Standby'}
                            </div>
                            <h2 className="text-3xl font-bold tracking-tight text-white">Transit Assistant</h2>
                            <p className="text-zinc-400 text-sm mt-1">"When is Route 22 coming?"</p>
                        </div>
                        <button onClick={startListening} 
                            className={`w-16 h-16 flex items-center justify-center rounded-2xl transition-all shadow-lg border border-white/10 ${isListening ? 'bg-red-500/20 text-red-400 animate-pulse border-red-500/50' : 'bg-white/5 text-indigo-400 hover:bg-white/10 hover:scale-105'}`}>
                            {isListening ? (
                                <div className="flex gap-1 h-4 items-center">
                                    <span className="w-1 bg-current animate-wave"></span>
                                    <span className="w-1 bg-current animate-wave delay-75"></span>
                                    <span className="w-1 bg-current animate-wave delay-150"></span>
                                </div>
                            ) : (
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8"><path d="M8.25 4.5a3.75 3.75 0 117.5 0v8.25a3.75 3.75 0 11-7.5 0V4.5z" /><path d="M6 10.5a.75.75 0 01.75.75v1.5a5.25 5.25 0 1010.5 0v-1.5a.75.75 0 011.5 0v1.5a6.751 6.751 0 01-6 9.364 6.75 6.75 0 01-6.75-6.75v-1.5a.75.75 0 01.75-.75z" /></svg>
                            )}
                        </button>
                    </div>
                    
                    {/* Transcript / Reply Area */}
                    <div className="mt-6 min-h-[80px]">
                        {transcript && (
                            <div className="text-right text-sm text-indigo-300 mb-2 font-mono opacity-80">"{transcript}"</div>
                        )}
                        <div className="bg-black/50 border border-white/10 backdrop-blur-md rounded-xl p-4 text-sm font-medium text-zinc-300 shadow-inner min-h-[60px] flex items-center">
                            {processingVoice ? (
                                <span className="flex items-center gap-2 text-indigo-400">
                                    <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></span>
                                    Processing Query...
                                </span>
                            ) : (
                                <span className={assistantReply ? 'text-white' : 'text-zinc-600 italic'}>
                                    {assistantReply || "Tap the microphone to ask about routes, delays, or schedules..."}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* 2. GREEN POINTS (Small Card) */}
            <div className="col-span-1 bg-gradient-to-b from-emerald-900/40 to-black/60 backdrop-blur-md border border-emerald-500/20 rounded-3xl p-6 relative overflow-hidden group hover:border-emerald-500/40 transition-all">
                <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-2xl -mr-8 -mt-8"></div>
                
                <div className="relative z-10 h-full flex flex-col justify-between">
                    <div className="flex justify-between items-start">
                        <span className="text-emerald-400 text-[10px] font-bold uppercase tracking-widest border border-emerald-500/20 px-2 py-1 rounded bg-emerald-900/20">Eco Impact</span>
                        <span className="text-2xl drop-shadow-lg">🌱</span>
                    </div>
                    <div>
                        <div className="flex items-baseline gap-1 mt-4">
                            <span className="text-5xl font-bold tracking-tighter text-white drop-shadow-[0_0_15px_rgba(16,185,129,0.3)]">{greenPoints}</span>
                            <span className="text-sm font-medium text-emerald-400/80">pts</span>
                        </div>
                        <div className="mt-4 bg-zinc-800/50 h-2 rounded-full overflow-hidden border border-white/5">
                            <div className="bg-gradient-to-r from-emerald-600 to-emerald-400 h-full w-[70%] shadow-[0_0_10px_rgba(16,185,129,0.5)]"></div>
                        </div>
                        <p className="text-[10px] text-zinc-400 mt-2 text-right font-mono">NEXT REWARD: FREE RIDE (250 PTS)</p>
                    </div>
                </div>
            </div>

            {/* 3. MANUAL SIGNAL (The Control Panel) */}
            <div className="col-span-1 md:col-span-2 lg:col-span-2 bg-black/40 backdrop-blur-md border border-white/10 rounded-3xl p-8 shadow-2xl">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-xl flex items-center justify-center font-bold shadow-lg shadow-blue-900/20">📍</div>
                    <h3 className="text-xl font-bold text-white">Broadcast Location</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-4">
                        <div className="group">
                            <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-2 ml-1">Select Route</label>
                            <div className="relative">
                                <select value={selectedRouteId} onChange={(e) => setSelectedRouteId(e.target.value)} 
                                    className="w-full bg-black/50 border border-white/10 hover:border-blue-500/50 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all appearance-none cursor-pointer">
                                    <option value="" className="bg-zinc-900">-- Select Route --</option>
                                    {BANGALORE_ROUTES.map(r => <option key={r.id} value={r.id} className="bg-zinc-900">{r.id}: {r.name}</option>)}
                                </select>
                                <div className="absolute right-4 top-3.5 text-zinc-500 pointer-events-none text-xs">▼</div>
                            </div>
                        </div>
                        {activeRoute && (
                            <div className="group animate-fade-in">
                                <label className="block text-[9px] font-bold text-zinc-500 uppercase tracking-widest mb-2 ml-1">Select Stop</label>
                                <div className="relative">
                                    <select value={selectedStop} onChange={(e) => setSelectedStop(e.target.value)} 
                                        className="w-full bg-black/50 border border-white/10 hover:border-blue-500/50 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all appearance-none cursor-pointer">
                                        <option value="" className="bg-zinc-900">-- Select Stop --</option>
                                        <option value={activeRoute.waypoints[0]?.name} className="bg-zinc-900">Start Point</option>
                                        {activeRoute.waypoints.map((wp, i) => <option key={i} value={wp.name} className="bg-zinc-900">{wp.name}</option>)}
                                    </select>
                                    <div className="absolute right-4 top-3.5 text-zinc-500 pointer-events-none text-xs">▼</div>
                                </div>
                            </div>
                        )}
                    </div>
                    
                    <div className="flex flex-col justify-end">
                        <button onClick={handleImComing} disabled={signaling || !selectedStop} 
                            className="w-full h-[84px] bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-lg font-bold rounded-xl shadow-[0_0_20px_rgba(37,99,235,0.3)] border border-blue-400/20 transform active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center gap-3 relative overflow-hidden group">
                            {signaling ? (
                                <span className="animate-pulse">Broadcasting Signal...</span>
                            ) : (
                                <>
                                    <span className="text-2xl group-hover:animate-bounce">👋</span> 
                                    <span>Signal Bus Driver</span>
                                </>
                            )}
                            <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-20 transition-opacity"></div>
                        </button>
                    </div>
                </div>
                
                {lastSignal && (
                    <div className="mt-6 bg-emerald-900/20 border border-emerald-500/20 p-4 rounded-xl flex items-center gap-3 animate-fade-in">
                        <div className="w-6 h-6 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center text-xs border border-emerald-500/30">✓</div>
                        <p className="text-xs text-emerald-200">
                            <strong className="text-emerald-400">Signal Received:</strong> Driver notified you are waiting at <span className="text-white">{lastSignal.stop}</span> for <span className="text-white">{lastSignal.route}</span>.
                        </p>
                    </div>
                )}
            </div>

            {/* 4. FEEDBACK */}
            <div className="col-span-1 bg-black/40 backdrop-blur-md border border-white/10 rounded-3xl p-6 shadow-xl flex flex-col">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-yellow-500/10 text-yellow-500 border border-yellow-500/20 rounded-lg flex items-center justify-center text-lg shadow-lg shadow-yellow-900/20">⭐</div>
                    <h3 className="font-bold text-white text-sm uppercase tracking-wider">Rate Ride</h3>
                </div>
                
                <div className="flex justify-between bg-black/50 border border-white/5 p-3 rounded-xl mb-4">
                    {[1,2,3,4,5].map(star => (
                        <button key={star} onClick={() => setRating(star)} className={`text-2xl transition-all hover:scale-110 ${rating >= star ? 'grayscale-0 drop-shadow-[0_0_8px_rgba(234,179,8,0.5)]' : 'grayscale opacity-20'}`}>⭐</button>
                    ))}
                </div>
                
                <textarea value={reviewText} onChange={e=>setReviewText(e.target.value)} placeholder="How was the cleanliness, timing, or staff behavior?" 
                    className="w-full p-3 bg-black/50 border border-white/10 rounded-xl h-24 resize-none text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-yellow-500/50 focus:ring-1 focus:ring-yellow-500/20 mb-3 flex-grow transition-colors" />
                
                <button onClick={handleReview} disabled={reviewing || !selectedRouteId} 
                    className="w-full bg-gradient-to-r from-yellow-600 to-amber-600 hover:from-yellow-500 hover:to-amber-500 text-white font-bold py-3 rounded-xl shadow-lg border border-yellow-500/20 transition-all disabled:opacity-50 text-xs uppercase tracking-widest">
                    {reviewing ? 'Submitting...' : 'Submit Review'}
                </button>
            </div>

        </div>
      </div>

      <style jsx global>{`
        @keyframes gradient-xy {
            0%, 100% { background-position: 0% 0%; }
            50% { background-position: 100% 100%; }
        }
        .animate-gradient {
            background-size: 200% 200%;
            animation: gradient-xy 15s ease infinite;
        }
        .animate-fade-in { animation: fadeIn 0.4s ease-out forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        
        .animate-wave { animation: wave 1s ease-in-out infinite; }
        @keyframes wave { 0%, 100% { height: 4px; } 50% { height: 16px; } }
      `}</style>
    </div>
  );
}
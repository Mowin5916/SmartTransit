'use client';
import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function PassengerCounter({ busId }: { busId: string }) {
  const [occupancy, setOccupancy] = useState(0);
  const [capacity, setCapacity] = useState(40);

  useEffect(() => {
    if (!busId) return;

    // 1. Fetch initial state
    const fetchData = async () => {
      const { data } = await supabase
        .from('buses')
        .select('current_occupancy, capacity')
        .eq('id', busId)
        .single();
      
      if (data) {
        setOccupancy(data.current_occupancy);
        setCapacity(data.capacity);
      }
    };
    fetchData();

    // 2. Subscribe to Realtime changes
    const channel = supabase
      .channel(`bus-${busId}`)
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'buses', filter: `id=eq.${busId}` },
        (payload) => {
          setOccupancy(payload.new.current_occupancy);
        }
      )
      .subscribe();

    return () => { supabase.removeChannel(channel); };
  }, [busId]);

  const percentage = Math.min(100, (occupancy / capacity) * 100);
  const color = percentage > 90 ? 'bg-red-500' : percentage > 50 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div className="bg-white p-4 rounded-xl shadow border border-gray-200 mt-4">
      <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">Live Occupancy</h3>
      <div className="flex items-end gap-2">
        <span className="text-4xl font-black text-gray-800">{occupancy}</span>
        <span className="text-gray-400 mb-1">/ {capacity}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2 overflow-hidden">
        <div className={`${color} h-2.5 transition-all duration-500`} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}
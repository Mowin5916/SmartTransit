'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';

export default function PassengerCounter({ busId }: { busId: string }) {
  const [occupancy, setOccupancy] = useState<number>(0);
  const [capacity, setCapacity] = useState<number>(40);

  useEffect(() => {
    if (!busId) return;

    let mounted = true;

    // 1️⃣ Initial fetch
    const fetchData = async () => {
      const { data, error } = await supabase
        .from('buses')
        .select('current_occupancy, capacity')
        .eq('id', busId)
        .single();

      if (!error && data && mounted) {
        setOccupancy(data.current_occupancy ?? 0);
        setCapacity(data.capacity ?? 40);
      }
    };

    fetchData();

    // 2️⃣ Realtime subscription
    const channel = supabase
      .channel(`bus-${busId}`)
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'buses',
          filter: `id=eq.${busId}`,
        },
        (payload) => {
          if (payload?.new?.current_occupancy !== undefined) {
            setOccupancy(payload.new.current_occupancy);
          }
        }
      )
      .subscribe();

    return () => {
      mounted = false;
      supabase.removeChannel(channel);
    };
  }, [busId]);

  const percentage =
    capacity > 0 ? Math.min(100, (occupancy / capacity) * 100) : 0;

  const color =
    percentage > 90
      ? 'bg-red-500'
      : percentage > 60
      ? 'bg-yellow-500'
      : 'bg-green-500';

  return (
    <div className="bg-white p-4 rounded-xl shadow border border-gray-200 mt-4">
      <h3 className="text-gray-500 text-sm font-bold uppercase mb-2">
        Live Occupancy
      </h3>

      <div className="flex items-end gap-2">
        <span className="text-4xl font-black text-gray-800">
          {occupancy}
        </span>
        <span className="text-gray-400 mb-1">/ {capacity}</span>
      </div>

      <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2 overflow-hidden">
        <div
          className={`${color} h-2.5 transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

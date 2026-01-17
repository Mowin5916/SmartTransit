// lib/realtime.ts
import { supabase } from './supabase';

export function subscribeToProfiles(callback: (payload: any) => void) {
  const channel = supabase.channel('public:profiles')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'profiles' },
      (payload) => callback(payload)
    )
    .subscribe();

  return channel;
}

export function subscribeToTelemetry(callback: (payload: any) => void) {
  const channel = supabase.channel('public:telemetry')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'telemetry' },
      (payload) => callback(payload)
    )
    .subscribe();

  return channel;
}

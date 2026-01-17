// lib/supabase-provider.tsx
'use client';

import React, { createContext, useContext, useEffect, useMemo } from 'react';
import { supabase } from './supabase';

const SupabaseContext = createContext(supabase);

export const SupabaseProvider = ({ children }: { children: React.ReactNode }) => {
  const client = useMemo(() => supabase, []);

  useEffect(() => {
    // Helper: attempt to upsert profile using localStorage pending items
    async function maybeUpsertPendingProfile(userId: string) {
      try {
        if (!userId) return;
        const pendingRole = typeof window !== 'undefined' ? localStorage.getItem('pending_role') : null;
        const pendingName = typeof window !== 'undefined' ? localStorage.getItem('pending_name') : null;
        if (!pendingRole && !pendingName) return;

        const payload: any = { id: userId };
        if (pendingName) payload.full_name = pendingName;
        if (pendingRole) payload.role = pendingRole;

        const { data, error } = await supabase.from('profiles').upsert(payload).select('*');
        if (error) {
          console.error('Supabase upsert profile error:', error);
        } else {
          try {
            localStorage.removeItem('pending_role');
            localStorage.removeItem('pending_name');
          } catch {}
        }
      } catch (err) {
        console.error('maybeUpsertPendingProfile error', err);
      }
    }

    // on mount: check current session
    supabase.auth.getSession().then(({ data }) => {
      const session = data.session;
      if (session?.user?.id) {
        maybeUpsertPendingProfile(session.user.id);
      }
    });

    // subscribe to auth changes
    const { data: listener } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user?.id) {
        maybeUpsertPendingProfile(session.user.id);
      }
    });

    return () => {
      listener?.subscription.unsubscribe();
    };
  }, []);

  return <SupabaseContext.Provider value={client}>{children}</SupabaseContext.Provider>;
};

export const useSupabase = () => useContext(SupabaseContext);

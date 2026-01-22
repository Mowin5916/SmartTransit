import { supabase } from './supabase';

// Environmental Variable for your External Python AI Backend (if available)
const SMARTTRANSIT_API = process.env.NEXT_PUBLIC_SMARTTRANSIT_API || '';

// ==========================================
// 1. TYPE DEFINITIONS
// ==========================================

export type RouteCoord = { lat: number; lng: number };

export type RouteRecord = {
  id: string;
  name?: string;
  coords?: RouteCoord[];
  stops?: string[];
};

export type BusRecord = {
  id: string;
  plate_number: string;
  route_id?: string;
  driver_id?: string;
  capacity: number;
  current_occupancy: number;
  status: string; // 'active', 'maintenance', etc.
};

export type UserProfile = {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  role: string; // 'driver' | 'conductor' | 'admin' | 'passenger'
  created_at: string;
  avatar_url?: string;
};

export type WorkLog = {
  id: number;
  route_name: string;
  date: string;
  status: string;
  hours: number;
};

export type PredictionPayload = {
  time_slot?: number;
  live_congestion?: number;
  usual_congestion?: number;
  route_features: {
    Route_ID: number | string;
    Hour: number;
    Weather: number;
    Holiday: number;
  };
};

export type PredictionResult = {
  predicted_passengers: number;
  recommended_buses: number;
  overcrowding_risk: 'High' | 'Medium' | 'Low';
  speed_kmph: number;
  delay_min_per_10km: number;
  _mock?: boolean;
};

// ==========================================
// 2. CORE DATA (ROUTES, PROFILES, ASSIGNMENTS)
// ==========================================

/**
 * getRoutes
 * Fetches all routes. Handles normalization of coordinates/stops.
 */
export async function getRoutes(): Promise<RouteRecord[]> {
  const { data, error } = await supabase
    .from('routes')
    .select('id, name, stops, coords')
    .order('id', { ascending: true });

  if (error) {
    console.warn('getRoutes supabase error (returning empty):', error);
    return [];
  }

  if (!data) return [];

  // Normalize data types for coords/stops
  return (data as any[]).map((r) => {
    return {
      id: r.id,
      name: r.name ?? r.id,
      coords: Array.isArray(r.coords) ? r.coords : r.coords, // add JSON parse here if stored as string
      stops: Array.isArray(r.stops) ? r.stops : r.stops,
    } as RouteRecord;
  });
}

/**
 * listProfilesByRole
 * Returns list of users based on role (e.g., get all 'drivers')
 */
export async function listProfilesByRole(role: string) {
  const { data, error } = await supabase
    .from('profiles')
    .select('id, full_name, role, phone')
    .eq('role', role);

  if (error) {
    console.error(`listProfilesByRole (${role}) error:`, error);
    throw error;
  }
  return data || [];
}

/**
 * getProfileById
 * Fetches details for a specific user (e.g., to display Driver details to a Conductor)
 */
export async function getProfileById(userId: string): Promise<UserProfile | null> {
  if (!userId) return null;
  
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', userId)
    .single();

  if (error) {
    console.warn(`getProfileById error for ${userId}:`, error);
    return null;
  }
  return data;
}

/**
 * getWorkHistory
 * Fetches past trips. Includes a Mock Fallback if the database is empty.
 */
export async function getWorkHistory(userId: string): Promise<WorkLog[]> {
  // 1. Try fetching real data
  const { data, error } = await supabase
    .from('trip_logs') 
    .select('*')
    .eq('staff_id', userId)
    .order('date', { ascending: false })
    .limit(5);

  if (!error && data && data.length > 0) {
    return data;
  }

  // 2. Mock Data Fallback (for demo/development)
  return [
    { id: 1, route_name: 'Majestic - Whitefield', date: '2023-10-24', status: 'Completed', hours: 8 },
    { id: 2, route_name: 'Koramangala - Indiranagar', date: '2023-10-23', status: 'Completed', hours: 7.5 },
    { id: 3, route_name: 'Hebbal - Airport', date: '2023-10-20', status: 'Completed', hours: 9 },
    { id: 4, route_name: 'Silk Board - Marathahalli', date: '2023-10-18', status: 'Completed', hours: 8.5 },
  ];
}

/**
 * getAssignments
 * Returns all active route assignments.
 */
export async function getAssignments() {
  const { data, error } = await supabase
    .from('assignments')
    .select('*')
    .order('updated_at', { ascending: false });

  if (error) {
    console.error('getAssignments error', error);
    throw error;
  }
  return data || [];
}

/**
 * getAssignmentForUser
 * Checks if the current user is assigned to any route (as Driver or Conductor).
 */
export async function getAssignmentForUser(userId: string) {
  if (!userId) return null;

  // 🔹 1. Check conductor assignment FIRST
  const { data: conductorAssignment, error: conductorError } =
    await supabase
      .from('assignments')
      .select('*')
      .eq('conductor_id', userId)
      .maybeSingle();

  if (conductorError) {
    console.error('Conductor assignment error:', conductorError);
    throw conductorError;
  }

  if (conductorAssignment) {
    return conductorAssignment;
  }

  // 🔹 2. Fallback to driver assignment
  const { data: driverAssignment, error: driverError } =
    await supabase
      .from('assignments')
      .select('*')
      .eq('driver_id', userId)
      .maybeSingle();

  if (driverError) {
    console.error('Driver assignment error:', driverError);
    throw driverError;
  }

  return driverAssignment ?? null;
}


/**
 * assignStaffToRoute
 * Upserts an assignment. Requires user to be logged in.
 */
export async function assignStaffToRoute(
  routeId: string,
  driverId?: string | null,
  conductorId?: string | null
) {
  if (!routeId) throw new Error('routeId is required');

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) throw new Error('You must be logged in');

  // 🔒 SAFE payload: do NOT overwrite unless explicitly passed
  const payload: any = {
    route_id: routeId,
    active: true,
    updated_at: new Date().toISOString(),
  };

  if (driverId !== undefined) payload.driver_id = driverId;
  if (conductorId !== undefined) payload.conductor_id = conductorId;

  const { data, error } = await supabase
    .from('assignments')
    .upsert(payload, { onConflict: 'route_id' })
    .select('*')
    .single();

  if (error) {
    console.error('assignStaffToRoute error:', error);
    throw error;
  }

  return data;
}

// ==========================================
// 3. BUS TELEMETRY & PASSENGER COUNTING
// ==========================================

/**
 * getBusDetails
 * Fetches a single bus to get live occupancy/capacity.
 */
export async function getBusDetails(busId: string): Promise<BusRecord | null> {
  const { data, error } = await supabase
    .from('buses')
    .select('*')
    .eq('id', busId)
    .single();

  if (error) {
    console.warn('getBusDetails error (or table missing):', error);
    return null;
  }
  return data as BusRecord;
}

/**
 * updatePassengerCount
 * Calls Next.js API route to update count safely.
 * @param action 1 (Entered) or -1 (Exited)
 */
export async function updatePassengerCount(busId: string, action: 1 | -1) {
  try {
    const res = await fetch('/api/bus/passenger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bus_id: busId, action }),
    });

    if (!res.ok) {
      console.warn('Passenger API route unavailable, attempting logic...');
      return { success: false, message: 'API unavailable' };
    }
    return res.json();
  } catch (err) {
    console.error('updatePassengerCount error', err);
    throw err;
  }
}

// ==========================================
// 4. AI PREDICTION SERVICE
// ==========================================

/**
 * fetchCombinedPrediction
 * 1. Tries to call the Python AI Backend.
 * 2. Falls back to a sophisticated Mock algorithm if backend is offline.
 */
export async function fetchCombinedPrediction(
  payload: PredictionPayload
): Promise<PredictionResult> {
  // 1. Try Real Backend
  if (SMARTTRANSIT_API) {
    try {
      const url = `${SMARTTRANSIT_API.replace(/\/$/, '')}/predict/all`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        return await res.json();
      } else {
        const txt = await res.text().catch(() => '');
        console.warn(`Prediction API error ${res.status}: ${txt}`);
      }
    } catch (e) {
      console.warn('Backend API failed, switching to Mock Mode', e);
    }
  }

  // 2. Mock Fallback Logic (Simulates Network Latency)
  await new Promise((r) => setTimeout(r, 800));

  const { route_features, live_congestion = 0 } = payload;
  const hour = route_features.Hour;

  // Simulation Logic
  let predicted = 40 + Math.random() * 20; // Base baseline
  if (hour >= 8 && hour <= 10) predicted += 50; // Morning Peak
  if (hour >= 17 && hour <= 20) predicted += 60; // Evening Peak
  if (live_congestion && live_congestion > 70) predicted += 15; // Traffic effect

  const recBuses = Math.max(1, Math.ceil(predicted / 50));
  const congestionVal = live_congestion || 0;
  const speed = Math.max(10, 45 - congestionVal * 0.4); 
  const delay = Math.max(0, congestionVal * 0.2 - 5);

  return {
    predicted_passengers: Math.floor(predicted),
    recommended_buses: recBuses,
    overcrowding_risk: predicted > 80 ? 'High' : predicted > 50 ? 'Medium' : 'Low',
    speed_kmph: parseFloat(speed.toFixed(1)),
    delay_min_per_10km: parseFloat(delay.toFixed(1)),
    _mock: true,
  };
}

// ==========================================
// 5. INCIDENTS & REVIEWS
// ==========================================

export async function reportIncident(incident: {
  route_id: string;
  type: string;
  message: string;
}) {
  const { error } = await supabase.from('incidents').insert([{
    ...incident,
    reported_at: new Date().toISOString(),
    status: 'Open'
  }]);
  
  // Ignore "table not found" error for demo purposes
  if (error && error.code !== '42P01') {
    throw error;
  }
  return true;
}

export async function submitReview(review: {
  route_id: string;
  rating: number;
  comment: string;
}) {
  const { error } = await supabase.from('reviews').insert([{
    ...review,
    created_at: new Date().toISOString()
  }]);

  if (error && error.code !== '42P01') {
    throw error;
  }
  return true;
}

export async function getRecentIncidents() {
  const { data, error } = await supabase
    .from('incidents')
    .select('*')
    .eq('status', 'Open')
    .order('reported_at', { ascending: false })
    .limit(10);

  if (error) {
    if (error.code === '42P01') return []; // Table missing
    console.error('getRecentIncidents error', error);
    throw error;
  }
  return data || [];
}

export async function getRecentReviews() {
  const { data, error } = await supabase
    .from('reviews')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(10);

  if (error) {
    if (error.code === '42P01') return []; // Table missing
    console.error('getRecentReviews error', error);
    throw error;
  }
  return data || [];
}
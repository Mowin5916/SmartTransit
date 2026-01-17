import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

// Initialize Admin client to bypass security for hardware updates
// Make sure SUPABASE_SERVICE_ROLE_KEY is in your .env.local file
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY! 
);

export async function POST(req: Request) {
  try {
    const { bus_id, action } = await req.json(); // action: 1 (enter) or -1 (exit)

    if (!bus_id || !action) {
      return NextResponse.json({ error: 'Missing data' }, { status: 400 });
    }

    // Call the SQL function we created in Step 1
    const { error } = await supabase.rpc('update_occupancy', {
      bus_id_input: bus_id,
      change_amount: action
    });

    if (error) throw error;

    return NextResponse.json({ success: true });
  } catch (error: any) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
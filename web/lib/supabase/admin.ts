import 'server-only';
import { createClient } from '@supabase/supabase-js';
import type { Database } from '../types';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

/**
 * Privileged Supabase client using Service Role Key.
 * Marked 'server-only' so it can NEVER be bundled into client code.
 * Null if environment credentials are not configured (triggers mock/demo mode).
 */
export const adminClient = (supabaseUrl && serviceRoleKey)
  ? createClient<Database>(supabaseUrl, serviceRoleKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      },
    })
  : null;

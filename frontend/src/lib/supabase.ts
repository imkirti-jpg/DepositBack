import { createClient } from '@supabase/supabase-js';

import { authStorage } from '@/auth/storage';
import { env } from '@/config/env';

export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey, {
  auth: {
    storage: authStorage,
    persistSession: true,
    autoRefreshToken: true,
  },
});

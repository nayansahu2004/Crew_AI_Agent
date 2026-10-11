// File path: frontend/src/lib/supabaseClient.js
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

if (!supabaseUrl || !supabaseKey) {
  // Fails loudly in development rather than silently producing confusing
  // auth errors later -- a missing .env is the most common cause.
  throw new Error(
    "Missing VITE_SUPABASE_URL or VITE_SUPABASE_PUBLISHABLE_KEY. " +
      "Copy frontend/.env.example to frontend/.env and fill in real values."
  );
}

export const supabase = createClient(supabaseUrl, supabaseKey);
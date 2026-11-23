import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://hnoxyrpleckufiasdels.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "sb_publishable_kNcEZLbRWjsOQprxaQAB6A_ks4aRokC";

let supabaseInstance: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!supabaseInstance) {
    supabaseInstance = createClient(supabaseUrl, supabaseAnonKey, {
      realtime: {
        params: {
          eventsPerSecond: 10,
        },
      },
    });
  }
  return supabaseInstance;
}

export interface ActionQueueItem {
  id: string;
  contact_id?: string | null;
  action_type: "draft_comment" | "connection_note" | "follow_up";
  content: string;
  status: "pending_approval" | "approved" | "rejected" | "executed" | "dismissed";
  scheduled_for?: string | null;
  metadata?: {
    hooks?: string[];
    relevance_score?: number;
    target_url?: string;
    source?: string;
    builder?: Record<string, any>;
    [key: string]: any;
  };
  contact?: {
    full_name?: string;
    headline?: string;
    company?: string;
    location?: string;
    linkedin_url?: string;
  };
  created_at?: string;
  updated_at?: string;
}

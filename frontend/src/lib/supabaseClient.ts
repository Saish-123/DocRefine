import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://vuoustiwrjdbqdxbaoka.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ1b3VzdGl3cmpkYnFkeGJhb2thIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODc5OTQ1NjMsImV4cCI6MjEwMzU3MDU2M30.gdyjHWZHm933PgPYGic0rHEd_MutsHLwe0yLgUQJfBI';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

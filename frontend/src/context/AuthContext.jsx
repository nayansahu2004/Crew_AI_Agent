// File path: frontend/src/context/AuthContext.jsx
//
// Tracks the Supabase session AND the user's profile (name, company,
// etc. from our own backend). Components read both via useAuth().

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { api } from "../lib/apiClient";
import { supabase } from "../lib/supabaseClient";
import { profileFromMetadata } from "../lib/validation";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  const [profile, setProfile] = useState(null);
  const [profileError, setProfileError] = useState(null);

  // Read inside loadProfile without making a token refresh (which swaps
  // the session object roughly hourly) re-trigger the profile fetch.
  const sessionRef = useRef(null);
  sessionRef.current = session;
  const userId = session?.user?.id ?? null;

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const loadProfile = useCallback(async () => {
    if (!userId) {
      setProfile(null);
      setProfileError(null);
      return;
    }

    setProfileError(null);
    try {
      let loaded = await api.get("/api/users/me");

      // If the person filled in their details on the sign-up form, those
      // travelled with their account -- save them now so they aren't
      // asked twice. If that fails, they just see the form pre-filled.
      if (!loaded.profile_complete) {
        const fromSignUp = profileFromMetadata(sessionRef.current?.user?.user_metadata);
        if (fromSignUp) {
          try {
            loaded = await api.post("/api/users/me", fromSignUp);
          } catch {
            /* fall through to the form */
          }
        }
      }
      setProfile(loaded);
    } catch (err) {
      setProfileError(err.message);
    }
  }, [userId]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const value = {
    session,
    user: session?.user ?? null,
    loading,
    profile,
    setProfile,
    profileError,
    refreshProfile: loadProfile,
    // The details ride along in the account's metadata because there is
    // no session to call our backend with until the email is confirmed.
    signUp: (email, password, details) =>
      supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: details.name,
            job_title: details.job_title,
            company_name: details.company_name,
            phone: details.phone,
          },
        },
      }),
    signIn: (email, password) =>
      supabase.auth.signInWithPassword({ email, password }),
    signOut: () => supabase.auth.signOut(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
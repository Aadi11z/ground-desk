import { useEffect, useMemo, useState } from "react";
import { createClient, type Session } from "@supabase/supabase-js";

import { getClientConfig, getCurrentIdentity } from "./api";
import { ProductScreen } from "./components/ProductScreen";
import { SignInScreen } from "./components/SignInScreen";
import type { ClientConfig, Identity } from "./types";

export function App() {
  const [config, setConfig] = useState<ClientConfig | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [workspaceId, setWorkspaceId] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    getClientConfig().then(setConfig).catch((error: Error) => setNotice(error.message));
  }, []);

  const supabaseClient = useMemo(
    () =>
      config
        ? createClient(config.supabase_url, config.supabase_publishable_key)
        : null,
    [config],
  );

  useEffect(() => {
    if (!supabaseClient) return;

    supabaseClient.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabaseClient.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
    });
    return () => data.subscription.unsubscribe();
  }, [supabaseClient]);

  useEffect(() => {
    if (!session) {
      setIdentity(null);
      return;
    }

    getCurrentIdentity(session.access_token)
      .then((nextIdentity) => {
        setIdentity(nextIdentity);
        setWorkspaceId(nextIdentity.workspaces[0]?.id ?? "");
      })
      .catch((error: Error) => setNotice(error.message));
  }, [session]);

  if (!config) {
    return <main className="center">{notice ?? "Loading GroundDesk…"}</main>;
  }
  if (!supabaseClient) {
    return <main className="center">Supabase is not configured.</main>;
  }
  if (!session) {
    return (
      <SignInScreen
        supabaseClient={supabaseClient}
        onSessionChange={setSession}
        notice={notice}
        setNotice={setNotice}
      />
    );
  }
  if (identity && !workspaceId) {
    return <main className="center">Your organization has no available workspace.</main>;
  }
  if (!identity) {
    return <main className="center">Loading your organization…</main>;
  }

  return (
    <ProductScreen
      identity={identity}
      workspaceId={workspaceId}
      setWorkspaceId={setWorkspaceId}
      accessToken={session.access_token}
      onLogout={() => supabaseClient?.auth.signOut()}
      notice={notice}
      setNotice={setNotice}
    />
  );
}

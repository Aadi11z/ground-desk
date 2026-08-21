import { useState, type Dispatch, type FormEvent, type SetStateAction } from "react";
import type { Session, SupabaseClient } from "@supabase/supabase-js";

import { Notice } from "./Notice";

type SignInScreenProps = {
  supabaseClient: SupabaseClient;
  onSessionChange: Dispatch<SetStateAction<Session | null>>;
  notice: string | null;
  setNotice: Dispatch<SetStateAction<string | null>>;
};

export function SignInScreen({
  supabaseClient,
  onSessionChange,
  notice,
  setNotice,
}: SignInScreenProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setNotice(null);

    const formData = new FormData(event.currentTarget);
    const { data, error } = await supabaseClient.auth.signInWithPassword({
      email: String(formData.get("email")),
      password: String(formData.get("password")),
    });

    if (error) {
      setNotice(error.message);
    } else {
      onSessionChange(data.session);
    }
    setIsSubmitting(false);
  }

  return (
    <main className="auth">
      <section className="card">
        <div className="brand">
          <i />GroundDesk
        </div>
        <p className="eyebrow">Organization support intelligence</p>
        <h1>Sign in to your organization</h1>
        <p className="supporting">
          Use the work account your organization administrator has provisioned
          for you.
        </p>
        <Notice value={notice} />
        <form className="form" onSubmit={submit}>
          <label>
            Work email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          <button className="primary" disabled={isSubmitting}>
            {isSubmitting ? "Please wait…" : "Continue"}
          </button>
        </form>
      </section>
    </main>
  );
}

import { useState } from "react";
import { ArrowRight, ShieldCheck, Layers } from "lucide-react";
import { login, switchMode } from "../services/api";
export function LoginView() {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <main className="login-page">
      <section className="login-story">
        <span className="brand-mark">
          <Layers />
        </span>
        <div className="eyebrow">URBAN INTELLIGENCE / SIH 26124</div>
        <h1>
          A clearer view.
          <br />
          <em>A safer city.</em>
        </h1>
        <p>
          Connect to your command center to review fleet observations, inspect
          evidence, and coordinate a response.
        </p>
        <div className="login-assurance">
          <ShieldCheck size={22} />
          <span>Your city data, available to your team</span>
        </div>
      </section>
      <form
        className="login-form panel"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          const data = new FormData(e.currentTarget);
          try {
            await login(
              String(data.get("username")),
              String(data.get("password")),
            );
          } catch (err) {
            setError(err instanceof Error ? err.message : "Unable to sign in");
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="eyebrow">BACKEND START HERE</div>
        <h2>Welcome back</h2>
        <p>Use the account created by your team administrator.</p>
        <label>
          Username
          <input name="username" autoComplete="username" required autoFocus />
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
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button className="btn btn-primary btn-lg" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
          <ArrowRight size={18} />
        </button>
        <button className="btn btn-ghost" type="button" onClick={switchMode}>
          Explore the demo instead
        </button>
      </form>
    </main>
  );
}

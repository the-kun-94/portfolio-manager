import { useState } from "react";
import type { FormEvent } from "react";
import type { NextPage } from "next";
import Head from "next/head";
import { useRouter } from "next/router";

const Login: NextPage = () => {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Login failed.");
      }
      const next = typeof router.query.next === "string" ? router.query.next : "/";
      window.location.href = next;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Emotionless Executioner — Login</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>
      <div className="login-screen">
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="brand-mark login-brand">EMOTIONLESS EXECUTIONER</div>
          <label className="login-label">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoFocus
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="form-error">{error}</p> : null}
          <button type="submit" className="submit-btn submit-btn-buy" disabled={loading || !password}>
            {loading ? "Checking…" : "Enter"}
          </button>
        </form>
      </div>
    </>
  );
};

export default Login;

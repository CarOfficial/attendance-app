import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";
import { ApiError } from "../api";
import { Alert, Button, Field, Input } from "../components/ui";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "اتصال به سرور برقرار نشد. اینترنت را بررسی کنید.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="aurora relative flex min-h-dvh flex-col justify-center overflow-hidden px-6 py-10">
      <div className="pointer-events-none absolute -top-20 -right-16 h-64 w-64 rounded-full bg-purple-500/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 -left-16 h-72 w-72 rounded-full bg-gold-400/30 blur-3xl" />
      <div className="relative mx-auto w-full max-w-sm">
        <div className="mb-10 text-center">
          <div className="btn-gold mx-auto flex h-18 w-18 items-center justify-center rounded-3xl p-5 text-3xl font-bold shadow-2xl">
            ح
          </div>
          <h1 className="mt-5 text-3xl font-bold tracking-tight text-royal-gradient">ورود کارمندان</h1>
          <p className="mt-2 text-sm text-indigo-900/60">با نام کاربری و رمز عبور خود وارد شوید</p>
        </div>

        <form onSubmit={submit} className="glass-strong space-y-6 rounded-[2rem] p-7">
          {error && <Alert>{error}</Alert>}
          <Field label="نام کاربری">
            <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoCapitalize="none" required dir="ltr" />
          </Field>
          <Field label="رمز عبور">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required dir="ltr" />
          </Field>
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "در حال ورود…" : "ورود"}
          </Button>
        </form>
      </div>
    </div>
  );
}

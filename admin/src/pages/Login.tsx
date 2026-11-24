import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";
import { ApiError } from "../api";
import { Alert, BrandLogo, Button, Field, Input } from "../components/ui";

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
      setError(err instanceof ApiError ? err.message : "اتصال به سرور برقرار نشد");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="aurora relative flex min-h-dvh items-center justify-center overflow-hidden p-4">
      {/* floating light orbs */}
      <div className="pointer-events-none absolute -top-24 -right-16 h-80 w-80 rounded-full bg-purple-500/30 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-28 -left-20 h-96 w-96 rounded-full bg-gold-400/30 blur-3xl" />

      <div className="relative w-full max-w-md">
        <div className="mb-8 text-center">
          <BrandLogo className="mx-auto h-16 w-16 rounded-3xl shadow-2xl" letterClass="text-2xl" />
          <h1 className="mt-5 text-3xl font-bold tracking-tight text-royal-gradient">حضوریار</h1>
          <p className="mt-2 text-sm text-indigo-900/60">همراه هوشمند حضور و غیاب — ورود به پنل مدیریت</p>
        </div>

        <form onSubmit={submit} className="glass-strong space-y-6 rounded-[2rem] p-8">
          {error && <Alert>{error}</Alert>}
          <Field label="نام کاربری">
            <Input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required dir="ltr" />
          </Field>
          <Field label="رمز عبور">
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required dir="ltr" />
          </Field>
          <Button type="submit" disabled={busy} className="w-full py-3.5 text-base">
            {busy ? "در حال ورود…" : "ورود به پنل"}
          </Button>
        </form>
        <p className="mt-6 text-center text-xs text-indigo-900/50">نسخه ۱.۰ · حضوریار</p>
      </div>
    </div>
  );
}

import { useState, type FormEvent } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { Alert, Button, Card, Field, Input } from "../components/ui";
import type { TokenOut } from "../types";

export function ChangePasswordPage() {
  const { me, setToken, logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next.length < 8) return setError("رمز جدید باید حداقل ۸ کاراکتر باشد.");
    if (next !== confirm) return setError("تکرار رمز با رمز جدید یکسان نیست.");
    setBusy(true);
    try {
      const out = await api<TokenOut>("/auth/change-password", {
        method: "POST",
        body: { current_password: current, new_password: next },
      });
      await setToken(out.access_token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "خطای نامشخص");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="aurora min-h-dvh px-4 py-8">
      <div className="mx-auto max-w-sm space-y-4">
        <Alert tone="info">
          سلام {me?.full_name}. برای اولین ورود، لطفاً رمز عبور اولیه را به رمز دلخواه خود تغییر دهید.
        </Alert>
        <Card>
          <h1 className="mb-5 text-xl font-bold text-royal-gradient">تغییر رمز عبور</h1>
          <form onSubmit={submit} className="space-y-4">
            {error && <Alert>{error}</Alert>}
            <Field label="رمز عبور فعلی (اولیه)">
              <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required dir="ltr" autoComplete="current-password" />
            </Field>
            <Field label="رمز عبور جدید">
              <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} required dir="ltr" autoComplete="new-password" />
            </Field>
            <Field label="تکرار رمز عبور جدید">
              <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required dir="ltr" autoComplete="new-password" />
            </Field>
            <Button type="submit" disabled={busy} className="w-full">
              {busy ? "در حال ذخیره…" : "ذخیره و ادامه"}
            </Button>
          </form>
        </Card>
        <button onClick={logout} className="block w-full text-center text-sm text-indigo-900/60">خروج</button>
      </div>
    </div>
  );
}

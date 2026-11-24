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
    if (next.length < 8) return setError("رمز عبور جدید باید حداقل ۸ کاراکتر باشد");
    if (next !== confirm) return setError("تکرار رمز عبور با رمز جدید یکسان نیست");

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
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md space-y-4">
        <Alert tone="info">
          سلام {me?.full_name}. برای ادامه، لطفاً رمز عبور اولیه خود را تغییر دهید.
        </Alert>
        <Card title="تغییر رمز عبور">
          <form onSubmit={submit} className="space-y-5">
            {error && <Alert>{error}</Alert>}
            <Field label="رمز عبور فعلی">
              <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required dir="ltr" autoComplete="current-password" />
            </Field>
            <Field label="رمز عبور جدید" hint="حداقل ۸ کاراکتر">
              <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} required dir="ltr" autoComplete="new-password" />
            </Field>
            <Field label="تکرار رمز عبور جدید">
              <Input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required dir="ltr" autoComplete="new-password" />
            </Field>
            <div className="flex items-center justify-between pt-2">
              <button type="button" onClick={logout} className="text-sm text-slate-500 hover:underline">
                خروج
              </button>
              <Button type="submit" disabled={busy}>
                {busy ? "در حال ذخیره…" : "ذخیره رمز جدید"}
              </Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}

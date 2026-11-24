import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { getCurrentFix, LocationError } from "../location";
import { Alert, Button, Card, TextArea } from "../components/ui";
import { InstallHint } from "../components/InstallHint";
import { formatJalaliDate, formatTime, todayIso } from "../jalali";
import { toPersianMessage } from "../apiErrors";
import type { AttendanceRow, TodayOut } from "../types";

type Action = "check-in" | "check-out";

export function HomePage() {
  const { me } = useAuth();
  const [today, setToday] = useState<TodayOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ tone: "error" | "success"; text: string } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [now, setNow] = useState(() => new Date());
  const [showCheckout, setShowCheckout] = useState(false);
  const [description, setDescription] = useState("");

  const refresh = useCallback(async () => {
    try {
      setToday(await api<TodayOut>("/attendance/today"));
      setLoadError(null);
    } catch (e) {
      setLoadError(e instanceof ApiError ? e.message : "اتصال به سرور برقرار نشد.");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const t = setInterval(() => setNow(new Date()), 30_000);
    return () => clearInterval(t);
  }, [refresh]);

  const act = async (action: Action, workDescription?: string) => {
    setMessage(null);
    setBusy(true);
    try {
      const fix = await getCurrentFix();
      const rec = await api<AttendanceRow>(`/attendance/${action}`, {
        method: "POST",
        body: {
          latitude: fix.latitude,
          longitude: fix.longitude,
          accuracy_m: fix.accuracy_m,
          ...(workDescription ? { work_description: workDescription } : {}),
        },
      });
      setMessage({
        tone: "success",
        text: action === "check-in"
          ? `ورود شما ثبت شد: ${formatTime(rec.check_in_at)} — ${rec.branch_name}`
          : `خروج شما ثبت شد: ${formatTime(rec.check_out_at)} — ${rec.branch_name}`,
      });
      setShowCheckout(false);
      setDescription("");
      await refresh();
    } catch (e) {
      const text = e instanceof LocationError ? e.message
        : e instanceof ApiError ? toPersianMessage(e.message)
        : "خطای نامشخص. دوباره تلاش کنید.";
      setMessage({ tone: "error", text });
      if (e instanceof ApiError && workDescription) setShowCheckout(true);
    } finally {
      setBusy(false);
    }
  };

  const submitCheckout = async () => {
    const text = description.trim();
    if (text.length < 3) return;
    await act("check-out", text);
  };

  const status = today?.status;
  const rec = today?.record ?? null;
  const hour = now.getHours();
  const greeting = hour < 12 ? "صبح بخیر" : hour < 18 ? "ظهر بخیر" : "عصر بخیر";
  const firstName = me?.full_name?.split(" ")[0] ?? "";

  const isOut = status === "checked_in";
  const isDone = status === "checked_out";
  const canSubmitDescription = description.trim().length >= 3 && !busy;

  return (
    <div className="space-y-5">
      <header className="px-1">
        <p className="text-sm text-indigo-900/60">{formatJalaliDate(todayIso())}</p>
        <h1 className="mt-1 text-2xl font-bold tracking-tight text-royal-gradient">
          {greeting}، {firstName}
        </h1>
      </header>

      <InstallHint />

      {loadError && <Alert>{loadError}</Alert>}
      {message && <Alert tone={message.tone}>{message.text}</Alert>}

      <Card className="relative overflow-hidden text-center">
        <div className="pointer-events-none absolute -top-16 left-1/2 h-48 w-48 -translate-x-1/2 rounded-full bg-gold-300/25 blur-3xl" />
        <div className="relative">
          <StatusPill status={status} />

          <div className="my-8 flex justify-center">
            {isDone ? (
              <div className="flex h-52 w-52 flex-col items-center justify-center rounded-full border-2 border-dashed border-indigo-200 bg-white/50 text-indigo-900/70">
                <span className="text-xl font-bold">امروز تمام شد</span>
                <span className="mt-1 text-sm">تا فردا، خسته نباشید</span>
              </div>
            ) : (
              <div className="relative flex items-center justify-center">
                {/* soft pulsing halo */}
                <span className={`absolute h-60 w-60 rounded-full opacity-40 blur-xl ${isOut ? "bg-rose-400" : "bg-purple-500"} ${busy ? "" : "animate-pulse"}`} />
                <button
                  onClick={() => {
                    if (isOut) {
                      setDescription("");
                      setShowCheckout(true);
                    } else {
                      void act("check-in");
                    }
                  }}
                  disabled={busy || !today}
                  className={`relative flex h-52 w-52 flex-col items-center justify-center rounded-full text-white transition duration-300 active:scale-95 disabled:opacity-70 ${
                    isOut
                      ? "bg-gradient-to-br from-rose-400 via-rose-500 to-rose-700 shadow-[0_20px_60px_-10px_rgba(225,29,72,0.6)]"
                      : "bg-gradient-to-br from-purple-400 via-purple-600 to-indigo-900 shadow-[0_20px_60px_-10px_rgba(126,34,206,0.7)]"
                  }`}
                >
                  <span className="absolute inset-3 rounded-full border border-white/25" />
                  <span className="text-3xl font-bold drop-shadow">{busy ? "…" : isOut ? "ثبت خروج" : "ثبت ورود"}</span>
                  <span className="mt-1.5 text-xs text-white/80">
                    {busy ? "در حال دریافت موقعیت" : "با تایید موقعیت مکانی"}
                  </span>
                </button>
              </div>
            )}
          </div>

          {rec && (
            <div className="grid grid-cols-2 gap-3 text-sm">
              <TimeTile label="ورود" value={formatTime(rec.check_in_at)} />
              <TimeTile label="خروج" value={formatTime(rec.check_out_at)} />
              <p className="col-span-2 text-xs text-indigo-900/60">{rec.branch_name}</p>
            </div>
          )}
        </div>
      </Card>

      {rec?.work_description && (
        <Card className="p-4">
          <p className="text-xs font-medium text-indigo-900/60">شرح کار امروز</p>
          <p className="mt-1 text-sm leading-6 text-indigo-950">{rec.work_description}</p>
        </Card>
      )}

      <p className="px-2 text-center text-xs leading-5 text-indigo-900/55">
        برای ثبت، باید داخل محدوده‌ی دفتر باشید و دسترسی موقعیت مکانی فعال باشد.
      </p>

      {showCheckout && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-indigo-950/45 p-4 backdrop-blur-sm sm:items-center">
          <div className="glass-strong w-full max-w-md rounded-[1.75rem] p-6" role="dialog" aria-modal="true" aria-label="ثبت خروج">
            <h2 className="text-lg font-bold text-indigo-950">ثبت خروج</h2>
            <p className="mt-1 text-sm leading-6 text-indigo-900/65">
              برای ثبت خروج، شرح کارهای امروز الزامی است و برای مدیر ارسال می‌شود.
            </p>
            <TextArea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="مثلاً: تکمیل گزارش فروش و پاسخ به ایمیل‌های مشتریان"
              rows={4}
              className="mt-4"
            />
            {description.length > 0 && description.trim().length < 3 && (
              <p className="mt-2 text-xs text-rose-600">حداقل ۳ نویسه بنویسید.</p>
            )}
            <div className="mt-5 flex gap-3">
              <Button onClick={submitCheckout} disabled={!canSubmitDescription} className="flex-1">
                {busy ? "در حال ثبت…" : "ثبت خروج"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => setShowCheckout(false)}
                disabled={busy}
                className="ring-1 ring-indigo-200"
              >
                انصراف
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusPill({ status }: { status: TodayOut["status"] | undefined }) {
  if (!status) return <span className="text-sm text-indigo-900/60">در حال دریافت وضعیت…</span>;
  const map = {
    not_checked_in: { text: "هنوز ورود نکرده‌اید", cls: "bg-gold-100 text-gold-700 ring-gold-200" },
    checked_in: { text: "در محل کار هستید", cls: "bg-emerald-50 text-emerald-700 ring-emerald-200" },
    checked_out: { text: "امروز خارج شده‌اید", cls: "bg-indigo-100 text-indigo-800 ring-indigo-200" },
  }[status];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium ring-1 ring-inset ${map.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {map.text}
    </span>
  );
}

function TimeTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-white/60 p-4 ring-1 ring-white/80">
      <p className="text-xs text-indigo-900/60">{label}</p>
      <p className="mt-1 text-xl font-bold tabular-nums text-indigo-950">{value}</p>
    </div>
  );
}

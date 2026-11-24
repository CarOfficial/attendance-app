import { useEffect, useState, type FormEvent } from "react";
import { ApiError, getSchedule, updateSchedule } from "../api";
import { Alert, Button, Card, Field, Input } from "../components/ui";
import { formatDateTime } from "../jalali";
import type { ScheduleOut } from "../types";

/** ترتیب روزهای هفته از شنبه؛ مقدارها معادل روزهای هفته جاوااسکریپت (0=یکشنبه … 6=شنبه) */
const WEEK_DAYS: { value: number; label: string }[] = [
  { value: 5, label: "شنبه" },
  { value: 6, label: "یکشنبه" },
  { value: 0, label: "دوشنبه" },
  { value: 1, label: "سه‌شنبه" },
  { value: 2, label: "چهارشنبه" },
  { value: 3, label: "پنجشنبه" },
  { value: 4, label: "جمعه" },
];

export function SchedulePage() {
  const [schedule, setSchedule] = useState<ScheduleOut | null>(null);
  const [workDays, setWorkDays] = useState<number[]>([]);
  const [startTime, setStartTime] = useState("08:00");
  const [endTime, setEndTime] = useState("17:00");
  const [grace, setGrace] = useState(10);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getSchedule()
      .then((s) => {
        setSchedule(s);
        setWorkDays(s.work_days);
        setStartTime(s.start_time);
        setEndTime(s.end_time);
        setGrace(s.late_grace_minutes);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت برنامه کاری"));
  }, []);

  const toggleDay = (v: number) =>
    setWorkDays((cur) => (cur.includes(v) ? cur.filter((d) => d !== v) : [...cur, v]));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    if (workDays.length === 0) return setError("حداقل یک روز کاری را انتخاب کنید");
    setBusy(true);
    try {
      const updated = await updateSchedule({
        work_days: WEEK_DAYS.map((d) => d.value).filter((v) => workDays.includes(v)),
        start_time: startTime,
        end_time: endTime,
        late_grace_minutes: Number(grace),
      });
      setSchedule(updated);
      setWorkDays(updated.work_days);
      setStartTime(updated.start_time);
      setEndTime(updated.end_time);
      setGrace(updated.late_grace_minutes);
      setNotice("برنامه کاری ذخیره شد.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "خطا در ذخیره برنامه کاری");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">برنامه کاری</h1>
        <p className="mt-1 text-sm text-slate-500">
          روزهای کاری، ساعت ورود و خروج و مهلت تاخیر برای همه کارمندان
        </p>
      </div>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <Card
        title="تنظیمات برنامه کاری"
        actions={
          schedule?.updated_at ? (
            <span className="text-xs text-slate-500">آخرین بروزرسانی: {formatDateTime(schedule.updated_at)}</span>
          ) : undefined
        }
      >
        {!schedule && !error ? (
          <p className="py-8 text-center text-sm text-slate-500">در حال بارگذاری…</p>
        ) : (
          <form onSubmit={submit} className="space-y-6">
            <div className="space-y-3">
              <p className="text-sm font-medium text-indigo-950/80">روزهای کاری هفته</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-7">
                {WEEK_DAYS.map((d) => (
                  <label
                    key={d.value}
                    className={`flex cursor-pointer items-center justify-center gap-2 rounded-2xl px-3 py-3 text-sm font-medium transition ring-1 ring-inset ${
                      workDays.includes(d.value)
                        ? "btn-royal ring-purple-300"
                        : "glass text-indigo-900/70 ring-white/70 hover:bg-white/80"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={workDays.includes(d.value)}
                      onChange={() => toggleDay(d.value)}
                      className="h-4 w-4 accent-purple-700"
                    />
                    {d.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <Field label="ساعت شروع کار">
                <Input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
              </Field>
              <Field label="ساعت پایان کار">
                <Input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
              </Field>
              <Field label="مهلت تاخیر (دقیقه)" hint="تا این مدت بعد از ساعت شروع، تاخیر محسوب نمی‌شود">
                <Input
                  type="number"
                  min={0}
                  max={120}
                  value={grace}
                  onChange={(e) => setGrace(Number(e.target.value))}
                  required
                />
              </Field>
            </div>

            <div className="flex justify-end">
              <Button type="submit" disabled={busy}>
                {busy ? "در حال ذخیره…" : "ذخیره برنامه"}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}

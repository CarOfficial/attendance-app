import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { api, ApiError, qs } from "../api";
import { Alert, Card, Chip } from "../components/ui";
import { dayStatusMeta } from "../status";
import {
  addDaysIso,
  formatHours,
  formatJalaliDate,
  formatTime,
  todayIso,
  toFa,
  toFaTime,
  weekDayName,
  weekStartIso,
} from "../jalali";
import type { DayStateOut, WeekOut } from "../types";

/** هفته کاری: present / absent / leave / pending check-out for each day. */
export function WeekPage() {
  const [start, setStart] = useState(() => weekStartIso(todayIso()));
  const [week, setWeek] = useState<WeekOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setWeek(await api<WeekOut>(`/attendance/week${qs({ start })}`));
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "دریافت برنامه هفتگی ناموفق بود.");
    } finally {
      setLoading(false);
    }
  }, [start]);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = (week?.days ?? []).reduce(
    (acc, d) => {
      if (d.status === "present" || d.status === "working") acc.present += 1;
      else if (d.status === "leave") acc.leave += 1;
      else if (d.is_work_day && ["absent", "incomplete", "rejected"].includes(d.status)) acc.absent += 1;
      return acc;
    },
    { present: 0, absent: 0, leave: 0 },
  );

  const weekEnd = week?.end ?? addDaysIso(start, 6);

  return (
    <div className="space-y-5">
      <header className="flex items-start justify-between gap-3 px-1">
        <div>
          <h1 className="text-xl font-bold text-indigo-950">هفته کاری</h1>
          <p className="mt-1 text-sm text-indigo-900/60">
            {formatJalaliDate(start)} تا {formatJalaliDate(weekEnd)}
          </p>
        </div>
        <div className="flex gap-1.5">
          <WeekButton onClick={() => setStart(addDaysIso(start, -7))}>قبلی</WeekButton>
          <WeekButton onClick={() => setStart(weekStartIso(todayIso()))}>این هفته</WeekButton>
          <WeekButton onClick={() => setStart(addDaysIso(start, 7))}>بعدی</WeekButton>
        </div>
      </header>

      {error && <Alert>{error}</Alert>}

      <div className="grid grid-cols-3 gap-2.5">
        <Stat label="حاضر" value={counts.present} cls="text-emerald-700" />
        <Stat label="غایب" value={counts.absent} cls="text-rose-600" />
        <Stat label="مرخصی" value={counts.leave} cls="text-teal-700" />
      </div>

      {week && (
        <Card className="p-4">
          <p className="text-xs text-indigo-900/60">ساعت کاری رسمی</p>
          <p className="mt-1 text-sm font-semibold text-indigo-950">
            {toFaTime(week.schedule.start_time)} تا {toFaTime(week.schedule.end_time)}
            <span className="mr-2 text-xs font-normal text-indigo-900/55">
              (روزهای کاری: {week.schedule.work_days.map(dayShort).join("، ")})
            </span>
          </p>
        </Card>
      )}

      {loading && !week && <p className="text-sm text-indigo-900/60">در حال بارگذاری…</p>}

      <div className="space-y-2.5">
        {week?.days.map((day) => (
          <DayRow key={day.date} day={day} today={day.date === todayIso()} />
        ))}
      </div>

      <p className="px-2 text-center text-xs leading-5 text-indigo-900/50">
        خروج ثبت‌نشده را می‌توانید تا ۲۴ ساعت بعد از بخش «درخواست‌ها» ثبت کنید.
      </p>
      <Link
        to="/history"
        className="block text-center text-xs font-medium text-indigo-700 underline decoration-indigo-300 underline-offset-4"
      >
        مشاهده سوابق ۳۰ روزه
      </Link>
    </div>
  );
}

function WeekButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="rounded-xl bg-white/70 px-3 py-2 text-xs font-medium text-indigo-800 ring-1 ring-indigo-200"
    >
      {children}
    </button>
  );
}

function Stat({ label, value, cls }: { label: string; value: number; cls: string }) {
  return (
    <div className="glass rounded-2xl px-3 py-3 text-center">
      <p className={`text-2xl font-bold tabular-nums ${cls}`}>{toFa(value)}</p>
      <p className="mt-0.5 text-[11px] text-indigo-900/60">{label}</p>
    </div>
  );
}

const DAY_SHORT: Record<number, string> = {
  0: "دوشنبه",
  1: "سه‌شنبه",
  2: "چهارشنبه",
  3: "پنجشنبه",
  4: "جمعه",
  5: "شنبه",
  6: "یکشنبه",
};

function dayShort(day: number): string {
  return DAY_SHORT[day] ?? String(day);
}

function DayRow({ day, today }: { day: DayStateOut; today: boolean }) {
  const meta = dayStatusMeta(day.status);
  const showTimes = day.check_in_at || day.check_out_at;

  return (
    <Card className={`p-4 ${today ? "ring-2 ring-purple-400/70" : ""}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-indigo-950">
            {weekDayName(day.date)}
            <span className="mr-2 text-xs font-normal text-indigo-900/55">{formatJalaliDate(day.date)}</span>
          </p>
          {showTimes ? (
            <p className="mt-1 text-xs tabular-nums text-indigo-900/65">
              ورود {formatTime(day.check_in_at)} · خروج {formatTime(day.check_out_at)}
              {day.hours_worked != null ? ` · ${formatHours(day.hours_worked)}` : ""}
            </p>
          ) : (
            <p className="mt-1 text-xs text-indigo-900/50">{day.is_work_day ? "بدون ثبت" : "روز غیرکاری"}</p>
          )}
        </div>
        <Chip className={meta.chip}>{meta.label}</Chip>
      </div>

      {(day.is_late || day.left_early || day.pending_leave || day.late_request_status === "pending") && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {day.is_late && <Chip className="bg-gold-100 text-gold-700 ring-gold-200">تاخیر</Chip>}
          {day.left_early && <Chip className="bg-orange-100 text-orange-700 ring-orange-200">خروج زودتر</Chip>}
          {day.pending_leave && (
            <Chip className="bg-indigo-50 text-indigo-700 ring-indigo-200">مرخصی در انتظار تایید</Chip>
          )}
          {day.late_request_status === "pending" && (
            <Chip className="bg-gold-100 text-gold-700 ring-gold-200">درخواست خروج در انتظار</Chip>
          )}
        </div>
      )}

      {day.work_description && (
        <p className="mt-3 rounded-xl bg-white/60 px-3 py-2 text-xs leading-6 text-indigo-900/75">
          {day.work_description}
        </p>
      )}
      {day.approval_note && (
        <p className="mt-2 text-xs text-indigo-900/55">یادداشت مدیر: {day.approval_note}</p>
      )}
    </Card>
  );
}

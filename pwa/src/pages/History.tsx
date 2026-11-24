import { useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { Alert, Card } from "../components/ui";
import { addDaysIso, formatJalaliDate, formatTime, todayIso, toFa } from "../jalali";
import type { AttendanceRow } from "../types";

export function HistoryPage() {
  const [rows, setRows] = useState<AttendanceRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const to = todayIso();
  const from = addDaysIso(to, -30);

  useEffect(() => {
    api<AttendanceRow[]>(`/attendance/history?from_date=${from}&to_date=${to}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت سوابق"));
  }, [from, to]);

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-bold text-slate-900">سوابق حضور</h1>
        <p className="mt-1 text-sm text-slate-500">۳۰ روز گذشته</p>
      </header>

      {error && <Alert>{error}</Alert>}
      {!rows && !error && <p className="text-sm text-slate-500">در حال بارگذاری…</p>}
      {rows?.length === 0 && <Card><p className="text-center text-sm text-slate-500">سابقه‌ای ثبت نشده است.</p></Card>}

      <div className="space-y-3">
        {rows?.map((r) => (
          <Card key={r.id} className="p-4">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-900">{formatJalaliDate(r.work_date)}</span>
              <span className="text-xs text-slate-500">{duration(r)}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm tabular-nums">
              <span className="text-slate-600">ورود: <b className="text-slate-900">{formatTime(r.check_in_at)}</b></span>
              <span className="text-slate-600">خروج: <b className="text-slate-900">{formatTime(r.check_out_at)}</b></span>
            </div>
            <p className="mt-2 text-xs text-slate-500">{r.branch_name}{r.edited_by_admin ? " · اصلاح‌شده توسط مدیر" : ""}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

function duration(r: AttendanceRow): string {
  if (!r.check_out_at) return "در حال حضور";
  const ms = new Date(r.check_out_at).getTime() - new Date(r.check_in_at).getTime();
  const totalMin = Math.max(0, Math.round(ms / 60000));
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return `${toFa(h)} ساعت و ${toFa(m)} دقیقه`;
}

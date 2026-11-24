import { useEffect, useState } from "react";
import { ApiError, api, downloadExcel, getSummary } from "../api";
import { Alert, Badge, Button, Card, Empty, Field, Select, Stat, Table } from "../components/ui";
import { JalaliDateField } from "../components/JalaliDateField";
import { addDaysIso, formatHours, formatJalaliDate, formatTime, todayIso } from "../jalali";
import { APPROVAL_STATUS, DAY_STATUS, weekdayName } from "../status";
import type { Employee, SummaryOut } from "../types";

export function ReportsPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [userId, setUserId] = useState("");
  const [from, setFrom] = useState(addDaysIso(todayIso(), -29));
  const [to, setTo] = useState(todayIso());
  const [summary, setSummary] = useState<SummaryOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"one" | "all" | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    api<Employee[]>("/admin/employees")
      .then((list) => {
        setEmployees(list);
        // گزارش تک‌کارمنده است؛ اولین کارمند به صورت پیش‌فرض انتخاب می‌شود
        setUserId((cur) => cur || (list.length > 0 ? String(list[0].id) : ""));
      })
      .catch(() => {});
  }, []);

  const load = () => {
    setError(null);
    getSummary({ user_id: userId, from_date: from, to_date: to })
      .then(setSummary)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت گزارش"));
  };

  useEffect(() => {
    if (userId) load();
    // eslint-disable-line react-hooks/exhaustive-deps
  }, [userId, from, to]);

  const shiftRange = (days: number) => {
    setFrom(addDaysIso(from, days));
    setTo(addDaysIso(to, days));
  };

  const thisWeek = () => {
    const dow = new Date().getDay(); // 0=یکشنبه … 6=شنبه
    const start = addDaysIso(todayIso(), -((dow + 1) % 7)); // شنبه همین هفته
    setFrom(start);
    setTo(addDaysIso(start, 6));
  };

  const download = async (scope: "one" | "all") => {
    setExportError(null);
    if (scope === "one" && !userId) {
      setExportError("برای دانلود اکسل یک کارمند را انتخاب کنید");
      return;
    }
    setExporting(scope);
    try {
      const blob = await downloadExcel(scope === "one" ? { user_id: userId, from_date: from, to_date: to } : { from_date: from, to_date: to });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `hozoor-yar-${from}_${to}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof ApiError ? e.message : "خطا در دریافت فایل اکسل");
    } finally {
      setExporting(null);
    }
  };

  const t = summary?.totals;
  const employeeName = userId ? employees.find((e) => String(e.id) === userId)?.full_name : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">گزارش و ساعات کاری</h1>
        <p className="mt-1 text-sm text-slate-500">
          {summary
            ? `${employeeName ?? "همه کارمندان"} — از ${formatJalaliDate(summary.from_date)} تا ${formatJalaliDate(summary.to_date)}`
            : "گزارش روزانه حضور، تاخیر و ساعت کاری"}
        </p>
      </div>

      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <Field label="کارمند">
            <Select value={userId} onChange={(e) => setUserId(e.target.value)}>
              {employees.length === 0 && <option value="">کارمندی ثبت نشده</option>}
              {employees.map((e) => (
                <option key={e.id} value={e.id}>{e.full_name}</option>
              ))}
            </Select>
          </Field>
          <Field label="از تاریخ">
            <JalaliDateField value={from} onChange={setFrom} />
          </Field>
          <Field label="تا تاریخ">
            <JalaliDateField value={to} onChange={setTo} />
          </Field>
          <div className="flex items-end gap-2">
            <Button variant="secondary" className="flex-1" onClick={load} disabled={!userId}>به‌روزرسانی</Button>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button variant="ghost" onClick={() => shiftRange(-7)}>هفته قبل</Button>
          <Button variant="ghost" onClick={thisWeek}>این هفته</Button>
          <Button variant="ghost" onClick={() => shiftRange(7)}>هفته بعد</Button>
          <span className="text-xs text-slate-500">بازه پیش‌فرض: ۳۰ روز اخیر</span>
        </div>
      </Card>

      <div className="flex flex-wrap gap-3">
        <Button
          variant="gold"
          onClick={() => download("one")}
          disabled={exporting !== null}
          title="دانلود اکسل برای کارمند انتخاب‌شده"
        >
          {exporting === "one" ? "در حال آماده‌سازی…" : "دانلود اکسل برای این کارمند"}
        </Button>
        <Button
          variant="secondary"
          onClick={() => download("all")}
          disabled={exporting !== null}
          title="دانلود اکسل همه کارمندان"
        >
          {exporting === "all" ? "در حال آماده‌سازی…" : "دانلود اکسل همه کارمندان"}
        </Button>
      </div>
      {exportError && <Alert>{exportError}</Alert>}
      {error && <Alert>{error}</Alert>}

      {t && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 xl:grid-cols-7">
          <Stat label="حاضر" value={t.present} tone="green" />
          <Stat label="غایب" value={t.absent} tone="rose" />
          <Stat label="مرخصی" value={t.leave} tone="amber" />
          <Stat label="در انتظار خروج" value={t.pending_checkout} tone="indigo" />
          <Stat label="مجموع ساعت کاری" value={formatHours(Number(t.total_hours))} tone="slate" />
          <Stat label="تعداد تاخیر" value={t.late_count} tone="rose" />
          <Stat label="خروج زودتر" value={t.early_leave_count} tone="amber" />
        </div>
      )}

      <Card title={summary ? `${summary.days.length} روز` : "در حال بارگذاری…"}>
        {!summary ? (
          <Empty>در حال دریافت گزارش…</Empty>
        ) : summary.days.length === 0 ? (
          <Empty>رکوردی در این بازه یافت نشد.</Empty>
        ) : (
          <Table head={[
            "تاریخ شمسی", "روز", "وضعیت", "ورود", "خروج", "ساعت کاری",
            "تاخیر", "خروج زودتر", "شرح کار", "وضعیت تایید",
          ]}>
            {summary.days.map((d) => {
              const st = DAY_STATUS[d.status];
              const ap = APPROVAL_STATUS[d.approval_status];
              return (
                <tr key={d.date}>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatJalaliDate(d.date)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">{weekdayName(d.date)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={st.tone}>{st.label}</Badge>
                    {d.pending_leave && <Badge tone="indigo">مرخصی در انتظار</Badge>}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatTime(d.check_in_at)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatTime(d.check_out_at)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums font-medium text-slate-800">
                    {formatHours(d.hours_worked)}
                  </td>
                  <td className="px-4 py-3">
                    {d.is_late ? <Badge tone="rose">تاخیر</Badge> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    {d.left_early ? <Badge tone="amber">زودتر</Badge> : <span className="text-slate-400">—</span>}
                  </td>
                  <td className="max-w-44 px-4 py-3 text-slate-600" title={d.work_description ?? undefined}>
                    <span className="line-clamp-2">{d.work_description || "—"}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={ap.tone}>{ap.label}</Badge>
                    {d.approval_note && (
                      <p className="mt-1 text-xs text-slate-500" title={d.approval_note}>یادداشت: {d.approval_note}</p>
                    )}
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>
    </div>
  );
}

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api";
import { Alert, Badge, Card, Empty, Stat, Table } from "../components/ui";
import { formatJalaliDate, formatTime, todayIso } from "../jalali";
import type { AttendanceRow, Dashboard } from "../types";

export function DashboardPage() {
  const [stats, setStats] = useState<Dashboard | null>(null);
  const [rows, setRows] = useState<AttendanceRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const today = todayIso();
    Promise.all([
      api<Dashboard>("/admin/dashboard"),
      api<AttendanceRow[]>(`/admin/attendance?from_date=${today}&to_date=${today}&limit=200`),
    ])
      .then(([s, r]) => {
        setStats(s);
        setRows(r);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت اطلاعات"));
  }, []);

  if (error) return <Alert>{error}</Alert>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">داشبورد</h1>
        <p className="mt-1 text-sm text-slate-500">
          امروز {stats ? formatJalaliDate(stats.date) : "…"}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="کارمندان فعال" value={stats?.active_employees ?? "—"} tone="indigo" />
        <Stat label="حاضر امروز" value={stats?.present_today ?? "—"} tone="green" />
        <Stat label="غایب امروز" value={stats?.absent_today ?? "—"} tone="rose" />
        <Stat label="در محل (ورود بدون خروج)" value={stats?.open_check_ins ?? "—"} tone="amber" />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Link to="/leaves" className="block transition hover:opacity-90" title="رفتن به صفحه مرخصی‌ها">
          <Stat label="مرخصی در انتظار" value={stats?.pending_leaves ?? "—"} tone="amber" />
        </Link>
        <Link to="/late-checkouts" className="block transition hover:opacity-90" title="رفتن به صفحه خروج فراموش‌شده">
          <Stat label="خروج فراموش‌شده در انتظار" value={stats?.pending_late_checkouts ?? "—"} tone="indigo" />
        </Link>
        <Link to="/leaves" className="block transition hover:opacity-90" title="مرخصی‌های تاییدشده امروز">
          <Stat label="مرخصی امروز" value={stats?.leave_today ?? "—"} tone="slate" />
        </Link>
        <Link to="/attendance" className="block transition hover:opacity-90" title="رکوردهای ردشده توسط مدیر">
          <Stat label="رد شده امروز" value={stats?.rejected_today ?? "—"} tone="rose" />
        </Link>
      </div>

      <Card title="ثبت‌های امروز">
        {rows.length === 0 ? (
          <Empty>هنوز کسی امروز ثبت ورود نکرده است.</Empty>
        ) : (
          <Table head={["کارمند", "دفتر", "ورود", "خروج", "وضعیت"]}>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-3 font-medium text-slate-800">{r.user_full_name}</td>
                <td className="px-4 py-3 text-slate-600">{r.branch_name}</td>
                <td className="px-4 py-3 tabular-nums">{formatTime(r.check_in_at)}</td>
                <td className="px-4 py-3 tabular-nums">{formatTime(r.check_out_at)}</td>
                <td className="px-4 py-3">
                  {r.check_out_at ? <Badge tone="slate">خارج شده</Badge> : <Badge tone="green">در محل</Badge>}
                </td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}

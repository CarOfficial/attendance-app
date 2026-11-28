import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, createHourlyLeave, decideHourlyLeave } from "../api";
import { Alert, Badge, Button, Card, DecisionDialog, Empty, Field, Input, Select, Table } from "../components/ui";
import { JalaliDateField } from "../components/JalaliDateField";
import { formatDateTime, formatJalaliDate, toFa, todayIso } from "../jalali";
import { LEAVE_STATUS } from "../status";
import type { DecisionIn, Employee, HourlyLeaveOut, LeaveStatus } from "../types";

const TABS: { key: "" | LeaveStatus; label: string }[] = [
  { key: "", label: "همه" },
  { key: "pending", label: "در انتظار" },
  { key: "approved", label: "تاییدشده" },
  { key: "rejected", label: "رد شده" },
];

/** 10.5 -> «۱۰:۳۰» */
function formatHour(hour: number): string {
  const h = Math.floor(hour);
  const m = Math.round((hour - h) * 60);
  return toFa(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
}

const HOURS = Array.from({ length: 49 }, (_, i) => i * 0.5); // 00:00 … 24:00

export function HourlyLeavesPage() {
  const [tab, setTab] = useState<"" | LeaveStatus>("pending");
  const [rows, setRows] = useState<HourlyLeaveOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [userId, setUserId] = useState("");
  const [date, setDate] = useState(todayIso());
  const [startHour, setStartHour] = useState(10);
  const [endHour, setEndHour] = useState(12);
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [deciding, setDeciding] = useState<{ leave: HourlyLeaveOut; decision: "approve" | "reject" } | null>(null);
  const [busy, setBusy] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    const q = tab ? `?status=${tab}` : "";
    api<HourlyLeaveOut[]>(`/admin/hourly-leaves${q}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت مرخصی‌های ساعتی"));
  };

  useEffect(load, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    api<Employee[]>("/admin/employees?include_inactive=false").then(setEmployees).catch(() => {});
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!userId) return setFormError("کارمند را انتخاب کنید");
    if (endHour <= startHour) return setFormError("ساعت پایان باید بعد از ساعت شروع باشد");
    if (reason.trim().length < 3) return setFormError("دلیل مرخصی را کامل بنویسید");
    setSaving(true);
    try {
      await createHourlyLeave({
        user_id: Number(userId),
        date,
        start_hour: startHour,
        end_hour: endHour,
        reason: reason.trim(),
      });
      setNotice("مرخصی ساعتی ثبت شد و در انتظار تصمیم است.");
      setShowForm(false);
      setReason("");
      setUserId("");
      load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "خطا در ثبت مرخصی ساعتی");
    } finally {
      setSaving(false);
    }
  };

  const confirm = async (note: string) => {
    if (!deciding) return;
    setBusy(true);
    setDecideError(null);
    const body: DecisionIn = { decision: deciding.decision };
    if (note) body.note = note;
    try {
      await decideHourlyLeave(deciding.leave.id, body);
      setNotice(
        deciding.decision === "approve"
          ? `مرخصی ساعتی ${deciding.leave.user_full_name} تایید شد.`
          : `مرخصی ساعتی ${deciding.leave.user_full_name} رد شد.`,
      );
      setDeciding(null);
      load();
    } catch (e) {
      setDecideError(e instanceof ApiError ? e.message : "خطا در ثبت تصمیم");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">مرخصی ساعتی</h1>
          <p className="mt-1 text-sm text-slate-500">
            مرخصی چندساعته کارمندان در یک روز؛ پس از تایید مدیر اعمال می‌شود
          </p>
        </div>
        <Button onClick={() => { setFormError(null); setShowForm(true); }}>ثبت مرخصی ساعتی</Button>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key || "all"}
            onClick={() => {
              setTab(t.key);
              setNotice(null);
            }}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              tab === t.key ? "btn-royal" : "glass text-indigo-900/70 hover:text-indigo-950"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <Card title={rows ? `${rows.length} درخواست` : "در حال بارگذاری…"}>
        {rows && rows.length === 0 ? (
          <Empty>درخواست مرخصی ساعتی‌ای با این وضعیت وجود ندارد.</Empty>
        ) : (
          <Table head={["نام کارمند", "تاریخ", "از ساعت", "تا ساعت", "دلیل", "وضعیت", "تاریخ ثبت", "عملیات"]}>
            {(rows ?? []).map((l) => {
              const st = LEAVE_STATUS[l.status];
              return (
                <tr key={l.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{l.user_full_name}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatJalaliDate(l.date)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatHour(l.start_hour)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatHour(l.end_hour)}</td>
                  <td className="max-w-56 px-4 py-3 text-slate-600" title={l.reason}>
                    <span className="line-clamp-2">{l.reason}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={st.tone}>{st.label}</Badge>
                    {l.decision_note && (
                      <p className="mt-1 text-xs text-slate-500" title={l.decision_note}>
                        یادداشت: {l.decision_note}
                      </p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDateTime(l.created_at)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    {l.status === "pending" ? (
                      <div className="flex gap-3">
                        <button
                          onClick={() => {
                            setDecideError(null);
                            setDeciding({ leave: l, decision: "approve" });
                          }}
                          className="text-emerald-600 hover:underline"
                        >
                          تایید
                        </button>
                        <button
                          onClick={() => {
                            setDecideError(null);
                            setDeciding({ leave: l, decision: "reject" });
                          }}
                          className="text-rose-600 hover:underline"
                        >
                          رد
                        </button>
                      </div>
                    ) : (
                      <span className="text-slate-400">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/35 p-4 backdrop-blur-sm">
          <form onSubmit={submit} className="w-full max-w-lg space-y-5 rounded-3xl glass-strong p-7">
            <div>
              <h2 className="text-lg font-bold text-slate-900">ثبت مرخصی ساعتی</h2>
              <p className="text-sm text-slate-500">ثبت مرخصی چندساعته برای یک کارمند در یک روز</p>
            </div>
            {formError && <Alert>{formError}</Alert>}
            <Field label="کارمند">
              <Select value={userId} onChange={(e) => setUserId(e.target.value)}>
                <option value="">انتخاب کنید…</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.full_name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="تاریخ">
              <JalaliDateField value={date} onChange={setDate} />
            </Field>
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="از ساعت">
                <Select value={startHour} onChange={(e) => setStartHour(Number(e.target.value))}>
                  {HOURS.map((h) => (
                    <option key={h} value={h}>
                      {toFa(formatHour(h))}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="تا ساعت">
                <Select value={endHour} onChange={(e) => setEndHour(Number(e.target.value))}>
                  {HOURS.map((h) => (
                    <option key={h} value={h}>
                      {toFa(formatHour(h))}
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
            <Field label="دلیل">
              <Input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="مثلاً مراجعه به پزشک" />
            </Field>
            {employees.length === 0 && <Empty>ابتدا در صفحه «کارمندان» حساب کارمند بسازید.</Empty>}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" type="button" onClick={() => setShowForm(false)}>
                انصراف
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? "در حال ثبت…" : "ثبت مرخصی"}
              </Button>
            </div>
          </form>
        </div>
      )}

      {deciding && (
        <DecisionDialog
          title={deciding.decision === "approve" ? "تایید مرخصی ساعتی" : "رد مرخصی ساعتی"}
          description={`${deciding.leave.user_full_name} — ${formatJalaliDate(deciding.leave.date)} از ${formatHour(
            deciding.leave.start_hour,
          )} تا ${formatHour(deciding.leave.end_hour)}`}
          confirmLabel={deciding.decision === "approve" ? "تایید شود" : "رد شود"}
          danger={deciding.decision === "reject"}
          busy={busy}
          error={decideError}
          onCancel={() => setDeciding(null)}
          onConfirm={confirm}
        />
      )}
    </div>
  );
}

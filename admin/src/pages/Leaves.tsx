import { useEffect, useState } from "react";
import { api, ApiError, decideLeave } from "../api";
import { Alert, Badge, Card, DecisionDialog, Empty, Table } from "../components/ui";
import { formatDateTime, formatJalaliDate } from "../jalali";
import { LEAVE_STATUS } from "../status";
import type { DecisionIn, LeaveOut, LeaveStatus } from "../types";

const TABS: { key: "" | LeaveStatus; label: string }[] = [
  { key: "", label: "همه" },
  { key: "pending", label: "در انتظار" },
  { key: "approved", label: "تاییدشده" },
  { key: "rejected", label: "رد شده" },
];

export function LeavesPage() {
  const [tab, setTab] = useState<"" | LeaveStatus>("pending");
  const [rows, setRows] = useState<LeaveOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deciding, setDeciding] = useState<{ leave: LeaveOut; decision: "approve" | "reject" } | null>(null);
  const [busy, setBusy] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    const q = tab ? `?status=${tab}` : "";
    api<LeaveOut[]>(`/admin/leaves${q}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت مرخصی‌ها"));
  };

  useEffect(load, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  const confirm = async (note: string) => {
    if (!deciding) return;
    setBusy(true);
    setDecideError(null);
    const body: DecisionIn = { decision: deciding.decision };
    if (note) body.note = note;
    try {
      await decideLeave(deciding.leave.id, body);
      setNotice(
        deciding.decision === "approve"
          ? `مرخصی ${deciding.leave.user_full_name} تایید شد.`
          : `مرخصی ${deciding.leave.user_full_name} رد شد.`,
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
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">مرخصی‌ها</h1>
        <p className="mt-1 text-sm text-slate-500">بررسی و تایید درخواست‌های مرخصی کارمندان</p>
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
          <Empty>درخواست مرخصی‌ای با این وضعیت وجود ندارد.</Empty>
        ) : (
          <Table head={["نام کارمند", "از", "تا", "دلیل", "وضعیت", "تاریخ ثبت", "عملیات"]}>
            {(rows ?? []).map((l) => {
              const st = LEAVE_STATUS[l.status];
              return (
                <tr key={l.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{l.user_full_name}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatJalaliDate(l.start_date)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatJalaliDate(l.end_date)}</td>
                  <td className="max-w-56 px-4 py-3 text-slate-600" title={l.reason}>
                    <span className="line-clamp-2">{l.reason}</span>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={st.tone}>{st.label}</Badge>
                    {l.decision_note && (
                      <p className="mt-1 text-xs text-slate-500" title={l.decision_note}>یادداشت: {l.decision_note}</p>
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

      {deciding && (
        <DecisionDialog
          title={deciding.decision === "approve" ? "تایید مرخصی" : "رد مرخصی"}
          description={`${deciding.leave.user_full_name} — از ${formatJalaliDate(deciding.leave.start_date)} تا ${formatJalaliDate(deciding.leave.end_date)}`}
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

import { useEffect, useState } from "react";
import { api, ApiError, decideLateCheckout } from "../api";
import { Alert, Badge, Card, DecisionDialog, Empty, Table } from "../components/ui";
import { formatDateTime, formatJalaliDate, formatTime } from "../jalali";
import { LATE_STATUS } from "../status";
import type { DecisionIn, LateCheckoutOut, LateCheckoutStatus } from "../types";

const TABS: { key: "" | LateCheckoutStatus; label: string }[] = [
  { key: "pending", label: "در انتظار" },
  { key: "approved", label: "تاییدشده" },
  { key: "rejected", label: "رد شده" },
  { key: "expired", label: "منقضی" },
  { key: "", label: "همه" },
];

export function LateCheckoutsPage() {
  const [tab, setTab] = useState<"" | LateCheckoutStatus>("pending");
  const [rows, setRows] = useState<LateCheckoutOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [deciding, setDeciding] = useState<{ row: LateCheckoutOut; decision: "approve" | "reject" } | null>(null);
  const [busy, setBusy] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);

  const load = () => {
    setError(null);
    const q = tab ? `?status=${tab}` : "";
    api<LateCheckoutOut[]>(`/admin/late-checkouts${q}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت درخواست‌ها"));
  };

  useEffect(load, [tab]); // eslint-disable-line react-hooks/exhaustive-deps

  const confirm = async (note: string) => {
    if (!deciding) return;
    setBusy(true);
    setDecideError(null);
    const body: DecisionIn = { decision: deciding.decision };
    if (note) body.note = note;
    try {
      await decideLateCheckout(deciding.row.id, body);
      setNotice(
        deciding.decision === "approve"
          ? `خروج ${deciding.row.user_full_name} در ${formatJalaliDate(deciding.row.work_date)} تایید شد.`
          : `درخواست خروج ${deciding.row.user_full_name} رد شد.`,
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
        <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">خروج فراموش‌شده</h1>
        <p className="mt-1 text-sm text-slate-500">
          بررسی درخواست‌های ثبت خروج توسط کارمندان؛ با تایید، ساعت ادعاشده روی رکورد روز ثبت می‌شود
        </p>
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
          <Empty>درخواستی با این وضعیت وجود ندارد.</Empty>
        ) : (
          <Table head={[
            "نام کارمند", "تاریخ روز", "ساعت خروج ادعاشده", "شرح کار", "فاصله از شعبه",
            "زمان ثبت", "مهلت تصمیم مدیر", "وضعیت", "عملیات",
          ]}>
            {(rows ?? []).map((r) => {
              const st = LATE_STATUS[r.status];
              return (
                <tr key={r.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{r.user_full_name}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatJalaliDate(r.work_date)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums font-semibold text-indigo-800">
                    {formatTime(r.check_out_at)}
                  </td>
                  <td className="max-w-48 px-4 py-3 text-slate-600" title={r.description ?? undefined}>
                    <span className="line-clamp-2">{r.description || "—"}</span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums text-slate-600">
                    {r.distance_m === null ? "—" : `${Math.round(r.distance_m)} متر`}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDateTime(r.requested_at)}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-slate-600">{formatDateTime(r.decision_deadline)}</td>
                  <td className="px-4 py-3">
                    <Badge tone={st.tone}>{st.label}</Badge>
                    {r.decision_note && (
                      <p className="mt-1 text-xs text-slate-500" title={r.decision_note}>یادداشت: {r.decision_note}</p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    {r.status === "pending" ? (
                      <div className="flex gap-3">
                        <button
                          onClick={() => {
                            setDecideError(null);
                            setDeciding({ row: r, decision: "approve" });
                          }}
                          className="text-emerald-600 hover:underline"
                        >
                          تایید
                        </button>
                        <button
                          onClick={() => {
                            setDecideError(null);
                            setDeciding({ row: r, decision: "reject" });
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
          title={deciding.decision === "approve" ? "تایید خروج فراموش‌شده" : "رد خروج فراموش‌شده"}
          description={
            `${deciding.row.user_full_name} — ${formatJalaliDate(deciding.row.work_date)} ساعت ${formatTime(deciding.row.check_out_at)}` +
            (deciding.decision === "reject" ? " (در صورت رد، آن روز غایب حساب می‌شود)" : "")
          }
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

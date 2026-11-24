import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { toPersianMessage } from "../apiErrors";
import { APPROVAL_META, requestStatusMeta } from "../status";
import { formatHours, formatJalaliDate, formatTime, toFa } from "../jalali";
import { Alert, Card, Chip } from "../components/ui";
import type {
  AdminDashboardOut,
  AttendanceOut,
  LateCheckoutOut,
  LeaveOut,
} from "../types";

type Section = "dash" | "leaves" | "lates" | "attendance";

const SECTIONS: { id: Section; label: string }[] = [
  { id: "dash", label: "داشبورد" },
  { id: "leaves", label: "مرخصی" },
  { id: "lates", label: "خروج فراموش‌شده" },
  { id: "attendance", label: "حضور" },
];

/** بخش مدیریت داخل اپ: مدیر با اکانت خودش وارد می‌شود و همین‌جا تایید/رد می‌کند. */
export function AdminPage() {
  const { me } = useAuth();
  const [section, setSection] = useState<Section>("dash");
  const [dash, setDash] = useState<AdminDashboardOut | null>(null);
  const [leaves, setLeaves] = useState<LeaveOut[]>([]);
  const [lates, setLates] = useState<LateCheckoutOut[]>([]);
  const [records, setRecords] = useState<AttendanceOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isAdmin = me?.role === "admin";

  const reload = useCallback(async () => {
    if (!isAdmin) return;
    try {
      const [d, l, c, a] = await Promise.all([
        api<AdminDashboardOut>("/admin/dashboard"),
        api<LeaveOut[]>("/admin/leaves?status=pending&limit=100"),
        api<LateCheckoutOut[]>("/admin/late-checkouts?status=pending&limit=100"),
        api<AttendanceOut[]>("/admin/attendance?limit=40"),
      ]);
      setDash(d);
      setLeaves(l);
      setLates(c);
      setRecords(a);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? toPersianMessage(e.message) : "دریافت اطلاعات مدیریت ناموفق بود.");
    }
  }, [isAdmin]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const decide = async (path: string, decision: "approve" | "reject", success: string) => {
    if (busy) return;
    setBusy(true);
    setNotice(null);
    try {
      await api(path, { method: "PATCH", body: { decision } });
      setNotice(success);
      await reload();
    } catch (e) {
      setError(e instanceof ApiError ? toPersianMessage(e.message) : "ثبت تصمیم ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  if (!isAdmin) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-indigo-950">بخش مدیریت</h1>
        <Alert>این بخش فقط برای حساب مدیر مجموعه قابل استفاده است.</Alert>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <header className="px-1">
        <h1 className="text-xl font-bold text-indigo-950">پنل مدیریت</h1>
        <p className="mt-1 text-sm text-indigo-900/60">{me?.full_name}</p>
      </header>

      <div className="scroll-thin -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSection(s.id)}
            className={`shrink-0 rounded-full px-4 py-2 text-xs font-medium transition ${
              section === s.id ? "btn-royal" : "bg-white/70 text-indigo-800 ring-1 ring-indigo-200"
            }`}
          >
            {s.label}
            {s.id === "leaves" && leaves.length > 0 ? ` (${toFa(leaves.length)})` : ""}
            {s.id === "lates" && lates.length > 0 ? ` (${toFa(lates.length)})` : ""}
          </button>
        ))}
      </div>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {section === "dash" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2.5">
            <Metric label="کارمندان فعال" value={dash?.active_employees} />
            <Metric label="حاضر امروز" value={dash?.present_today} tone="text-emerald-700" />
            <Metric label="غایب امروز" value={dash?.absent_today} tone="text-rose-600" />
            <Metric label="مرخصی امروز" value={dash?.leave_today} tone="text-teal-700" />
            <Metric label="در انتظار مرخصی" value={dash?.pending_leaves} tone="text-gold-700" />
            <Metric label="در انتظار خروج" value={dash?.pending_late_checkouts} tone="text-gold-700" />
          </div>
          <Card className="p-4">
            <p className="text-xs text-indigo-900/60">هم‌اکنون در محل کار</p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-indigo-950">
              {toFa(dash?.open_check_ins ?? 0)} نفر
            </p>
          </Card>
        </div>
      )}

      {section === "leaves" && (
        <div className="space-y-3">
          {leaves.length === 0 && <Empty text="درخواست مرخصی در انتظار تایید وجود ندارد." />}
          {leaves.map((leave) => (
            <Card key={leave.id} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-indigo-950">{leave.user_full_name}</p>
                  <p className="mt-1 text-xs text-indigo-900/60">
                    {formatJalaliDate(leave.start_date)} تا {formatJalaliDate(leave.end_date)}
                  </p>
                </div>
                <Chip className={requestStatusMeta(leave.status).chip}>
                  {requestStatusMeta(leave.status).label}
                </Chip>
              </div>
              <p className="mt-2 rounded-xl bg-white/60 px-3 py-2 text-xs leading-6 text-indigo-900/75">
                {leave.reason}
              </p>
              <Decision
                disabled={busy}
                onApprove={() =>
                  decide(`/admin/leaves/${leave.id}`, "approve", `مرخصی ${leave.user_full_name} تایید شد.`)
                }
                onReject={() =>
                  decide(`/admin/leaves/${leave.id}`, "reject", `مرخصی ${leave.user_full_name} رد شد.`)
                }
              />
            </Card>
          ))}
        </div>
      )}

      {section === "lates" && (
        <div className="space-y-3">
          {lates.length === 0 && <Empty text="درخواست خروج فراموش‌شده در انتظار تایید وجود ندارد." />}
          {lates.map((req) => (
            <Card key={req.id} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold text-indigo-950">{req.user_full_name}</p>
                  <p className="mt-1 text-xs text-indigo-900/60">
                    {formatJalaliDate(req.work_date)} · خروج {formatTime(req.check_out_at)}
                  </p>
                </div>
                <Chip className={requestStatusMeta(req.status).chip}>
                  {requestStatusMeta(req.status).label}
                </Chip>
              </div>
              <p className="mt-2 rounded-xl bg-white/60 px-3 py-2 text-xs leading-6 text-indigo-900/75">
                {req.description}
              </p>
              <p className="mt-2 text-[11px] text-indigo-900/55">
                {req.branch_name} · فاصله {toFa(Math.round(req.distance_m))} متر
              </p>
              <p className="mt-1 text-[11px] text-indigo-900/55">
                با رد کردن، آن روز برای کارمند غایب ثبت می‌شود.
              </p>
              <Decision
                disabled={busy}
                onApprove={() =>
                  decide(`/admin/late-checkouts/${req.id}`, "approve", "خروج تایید و روز حاضر شد.")
                }
                onReject={() =>
                  decide(`/admin/late-checkouts/${req.id}`, "reject", "درخواست رد شد؛ روز غایب ثبت شد.")
                }
              />
            </Card>
          ))}
        </div>
      )}

      {section === "attendance" && (
        <div className="space-y-3">
          {records.length === 0 && <Empty text="رکوردی برای نمایش وجود ندارد." />}
          {records.map((rec) => {
            const meta = APPROVAL_META[rec.approval_status];
            return (
              <Card key={rec.id} className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold text-indigo-950">{rec.user_full_name}</p>
                    <p className="mt-1 text-xs text-indigo-900/60">
                      {formatJalaliDate(rec.work_date)} · {rec.branch_name}
                    </p>
                  </div>
                  <Chip className={meta.chip}>{meta.label}</Chip>
                </div>
                <p className="mt-2 text-xs tabular-nums text-indigo-900/70">
                  ورود {formatTime(rec.check_in_at)} · خروج {formatTime(rec.check_out_at)}
                  {rec.hours_worked != null ? ` · ${formatHours(rec.hours_worked)}` : ""}
                </p>
                {rec.work_description && (
                  <p className="mt-2 rounded-xl bg-white/60 px-3 py-2 text-xs leading-6 text-indigo-900/75">
                    {rec.work_description}
                  </p>
                )}
                {rec.check_out_at && rec.approval_status === "none" && (
                  <Decision
                    disabled={busy}
                    onApprove={() =>
                      decide(`/admin/attendance/${rec.id}/decision`, "approve", "رکورد تایید شد.")
                    }
                    onReject={() =>
                      decide(`/admin/attendance/${rec.id}/decision`, "reject", "رکورد رد و غایب شد.")
                    }
                  />
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, tone = "text-indigo-950" }: { label: string; value?: number; tone?: string }) {
  return (
    <div className="glass rounded-2xl px-3 py-3 text-center">
      <p className={`text-2xl font-bold tabular-nums ${tone}`}>{value == null ? "—" : toFa(value)}</p>
      <p className="mt-0.5 text-[11px] text-indigo-900/60">{label}</p>
    </div>
  );
}

function Decision({
  onApprove,
  onReject,
  disabled,
}: {
  onApprove: () => void;
  onReject: () => void;
  disabled: boolean;
}) {
  return (
    <div className="mt-3 flex gap-2">
      <button
        onClick={onApprove}
        disabled={disabled}
        className="flex-1 rounded-xl bg-emerald-600 py-2.5 text-xs font-semibold text-white disabled:opacity-50"
      >
        تایید
      </button>
      <button
        onClick={onReject}
        disabled={disabled}
        className="flex-1 rounded-xl bg-white py-2.5 text-xs font-semibold text-rose-600 ring-1 ring-rose-200 disabled:opacity-50"
      >
        رد
      </button>
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <Card>
      <p className="text-center text-sm text-indigo-900/60">{text}</p>
    </Card>
  );
}

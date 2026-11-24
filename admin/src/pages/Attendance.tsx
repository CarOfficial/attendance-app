import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, decideAttendance } from "../api";
import { Alert, Badge, Button, Card, ConfirmDialog, DecisionDialog, Empty, Field, Input, Select, Table } from "../components/ui";
import { JalaliDateField } from "../components/JalaliDateField";
import { addDaysIso, formatHours, formatJalaliDate, formatTime, todayIso } from "../jalali";
import { APPROVAL_STATUS } from "../status";
import type { AttendanceRow, Branch, DecisionIn, Employee } from "../types";

/** Splits an ISO datetime into Tehran wall-clock date ("YYYY-MM-DD") and time ("HH:MM"). */
function isoToTehranParts(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: "", time: "" };
  const d = new Date(new Date(iso).getTime() + 3.5 * 3600 * 1000).toISOString();
  return { date: d.slice(0, 10), time: d.slice(11, 16) };
}

/** Tehran wall-clock date + time -> ISO string with the +03:30 offset. */
function tehranPartsToIso(date: string, time: string): string | null {
  if (!date) return null;
  return `${date}T${time || "00:00"}:00+03:30`;
}

export function AttendancePage() {
  const [from, setFrom] = useState(addDaysIso(todayIso(), -7));
  const [to, setTo] = useState(todayIso());
  const [userId, setUserId] = useState("");
  const [rows, setRows] = useState<AttendanceRow[] | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [editing, setEditing] = useState<AttendanceRow | null>(null);
  const [deciding, setDeciding] = useState<{ row: AttendanceRow; decision: "approve" | "reject" } | null>(null);
  const [decideBusy, setDecideBusy] = useState(false);
  const [decideError, setDecideError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<AttendanceRow | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Employee[]>("/admin/employees").then(setEmployees).catch(() => {});
    api<Branch[]>("/admin/branches").then(setBranches).catch(() => {});
  }, []);

  const load = () => {
    setError(null);
    const q = new URLSearchParams({ from_date: from, to_date: to, limit: "500" });
    if (userId) q.set("user_id", userId);
    api<AttendanceRow[]>(`/admin/attendance?${q}`)
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت گزارش"));
  };

  useEffect(load, [from, to, userId]); // eslint-disable-line react-hooks/exhaustive-deps

  const confirmDecision = async (note: string) => {
    if (!deciding) return;
    setDecideBusy(true);
    setDecideError(null);
    const body: DecisionIn = { decision: deciding.decision };
    if (note) body.note = note;
    try {
      await decideAttendance(deciding.row.id, body);
      setNotice(
        deciding.decision === "approve"
          ? `رکورد ${deciding.row.user_full_name} (${formatJalaliDate(deciding.row.work_date)}) تایید شد.`
          : `رکورد ${deciding.row.user_full_name} (${formatJalaliDate(deciding.row.work_date)}) رد شد.`,
      );
      setDeciding(null);
      load();
    } catch (e) {
      setDecideError(e instanceof ApiError ? e.message : "خطا در ثبت تصمیم");
    } finally {
      setDecideBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">حضور و غیاب</h1>
        <p className="mt-1 text-sm text-slate-500">
          از {formatJalaliDate(from)} تا {formatJalaliDate(to)}
        </p>
      </div>

      <Card>
        <div className="grid gap-4 md:grid-cols-4">
          <Field label="از تاریخ">
            <JalaliDateField value={from} onChange={setFrom} />
          </Field>
          <Field label="تا تاریخ">
            <JalaliDateField value={to} onChange={setTo} />
          </Field>
          <Field label="کارمند">
            <Select value={userId} onChange={(e) => setUserId(e.target.value)}>
              <option value="">همه کارمندان</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>{e.full_name}</option>
              ))}
            </Select>
          </Field>
          <div className="flex items-end">
            <Button variant="secondary" className="w-full" onClick={load}>به‌روزرسانی</Button>
          </div>
        </div>
      </Card>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <Card title={rows ? `${rows.length} رکورد` : "در حال بارگذاری…"}>
        {rows && rows.length === 0 ? (
          <Empty>رکوردی در این بازه یافت نشد.</Empty>
        ) : (
          <Table head={["تاریخ", "کارمند", "دفتر", "ورود", "خروج", "ساعت کاری", "شرح کار", "وضعیت", "وضعیت تایید", "عملیات"]}>
            {(rows ?? []).map((r) => {
              const ap = APPROVAL_STATUS[r.approval_status];
              return (
                <tr key={r.id}>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums">{formatJalaliDate(r.work_date)}</td>
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {r.user_full_name}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{r.branch_name}</td>
                  <td className="px-4 py-3 tabular-nums">{formatTime(r.check_in_at)}</td>
                  <td className="px-4 py-3 tabular-nums">{formatTime(r.check_out_at)}</td>
                  <td className="whitespace-nowrap px-4 py-3 tabular-nums font-medium text-slate-800">
                    {formatHours(r.hours_worked)}
                  </td>
                  <td className="max-w-44 px-4 py-3 text-slate-600" title={r.work_description ?? undefined}>
                    <span className="line-clamp-2">{r.work_description || "—"}</span>
                  </td>
                  <td className="px-4 py-3">
                    {r.edited_by_admin ? <Badge tone="amber">ویرایش دستی</Badge>
                      : r.check_out_at ? <Badge tone="slate">کامل</Badge>
                      : <Badge tone="green">باز</Badge>}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={ap.tone}>{ap.label}</Badge>
                    {r.approval_note && (
                      <p className="mt-1 text-xs text-slate-500" title={r.approval_note}>یادداشت: {r.approval_note}</p>
                    )}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    {r.check_out_at ? (
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
                      <span className="text-xs text-amber-700">خروج ثبت نشده؛ تصمیم ممکن نیست</span>
                    )}
                    <div className="mt-1 flex gap-3">
                      <button onClick={() => setEditing(r)} className="text-xs text-indigo-600 hover:underline">
                        ویرایش
                      </button>
                      <button
                        onClick={() => {
                          setDeleteError(null);
                          setDeleting(r);
                        }}
                        className="text-xs text-rose-600 hover:underline"
                      >
                        حذف
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </Table>
        )}
      </Card>

      {deciding && (
        <DecisionDialog
          title={deciding.decision === "approve" ? "تایید رکورد حضور" : "رد رکورد حضور"}
          description={`${deciding.row.user_full_name} — ${formatJalaliDate(deciding.row.work_date)}`}
          confirmLabel={deciding.decision === "approve" ? "تایید شود" : "رد شود"}
          danger={deciding.decision === "reject"}
          busy={decideBusy}
          error={decideError}
          onCancel={() => setDeciding(null)}
          onConfirm={confirmDecision}
        />
      )}

      {editing && (
        <EditRecordDialog
          row={editing}
          branches={branches}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}

      {deleting && (
        <ConfirmDialog
          title="حذف رکورد حضور"
          description={
            <>
              رکورد {deleting.user_full_name} در تاریخ {formatJalaliDate(deleting.work_date)} برای همیشه حذف می‌شود.
            </>
          }
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => setDeleting(null)}
          onConfirm={async () => {
            setDeleteBusy(true);
            setDeleteError(null);
            try {
              await api(`/admin/attendance/${deleting.id}`, { method: "DELETE" });
              setDeleting(null);
              setNotice("رکورد حضور حذف شد.");
              load();
            } catch (e) {
              setDeleteError(e instanceof ApiError ? e.message : "خطا در حذف رکورد");
            } finally {
              setDeleteBusy(false);
            }
          }}
        />
      )}
    </div>
  );
}

function EditRecordDialog({ row, branches, onClose, onSaved }: {
  row: AttendanceRow;
  branches: Branch[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [checkIn, setCheckIn] = useState(isoToTehranParts(row.check_in_at));
  const [checkOut, setCheckOut] = useState(isoToTehranParts(row.check_out_at));
  const [branchId, setBranchId] = useState(String(row.branch_id));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api(`/admin/attendance/${row.id}`, {
        method: "PATCH",
        body: {
          branch_id: Number(branchId),
          check_in_at: tehranPartsToIso(checkIn.date, checkIn.time) ?? undefined,
          check_out_at: tehranPartsToIso(checkOut.date, checkOut.time) ?? undefined,
        },
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "خطا در ذخیره");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/35 backdrop-blur-sm p-4">
      <form onSubmit={submit} className="w-full max-w-md space-y-5 glass-strong rounded-3xl p-7">
        <div>
          <h2 className="text-lg font-bold text-slate-900">ویرایش حضور</h2>
          <p className="text-sm text-slate-500">{row.user_full_name} — {formatJalaliDate(row.work_date)}</p>
        </div>
        {error && <Alert>{error}</Alert>}
        <Field label="ورود (تاریخ شمسی و ساعت تهران)">
          <div className="flex gap-2">
            <JalaliDateField
              value={checkIn.date}
              onChange={(iso) => setCheckIn((p) => ({ ...p, date: iso }))}
              className="flex-1"
            />
            <Input
              type="time"
              value={checkIn.time}
              onChange={(e) => setCheckIn((p) => ({ ...p, time: e.target.value }))}
              dir="ltr"
              className="w-28"
              required
            />
          </div>
        </Field>
        <Field label="خروج (تاریخ شمسی و ساعت تهران)" hint="خالی بگذارید تا تغییری نکند">
          <div className="flex gap-2">
            <JalaliDateField
              value={checkOut.date}
              onChange={(iso) => setCheckOut((p) => ({ ...p, date: iso }))}
              className="flex-1"
            />
            <Input
              type="time"
              value={checkOut.time}
              onChange={(e) => setCheckOut((p) => ({ ...p, time: e.target.value }))}
              dir="ltr"
              className="w-28"
            />
          </div>
        </Field>
        <Field label="دفتر">
          <Select value={branchId} onChange={(e) => setBranchId(e.target.value)}>
            {branches.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </Select>
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" type="button" onClick={onClose}>انصراف</Button>
          <Button type="submit" disabled={busy}>{busy ? "در حال ذخیره…" : "ذخیره"}</Button>
        </div>
      </form>
    </div>
  );
}

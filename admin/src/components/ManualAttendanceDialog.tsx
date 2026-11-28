import { useEffect, useState, type FormEvent } from "react";
import { api, ApiError, manualAttendance } from "../api";
import { Alert, Button, Empty, Field, Input, Select } from "./ui";
import { JalaliDateField } from "./JalaliDateField";
import { todayIso } from "../jalali";
import type { Branch, Employee } from "../types";

export function ManualAttendanceDialog({ onClose, onSaved }: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [userId, setUserId] = useState("");
  const [branchId, setBranchId] = useState("");
  const [date, setDate] = useState(todayIso());
  const [checkIn, setCheckIn] = useState("08:00");
  const [checkOut, setCheckOut] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Employee[]>("/admin/employees").then(setEmployees).catch(() => {});
    api<Branch[]>("/admin/branches").then((bs) => {
      setBranches(bs);
      if (bs.length) setBranchId(String(bs[0].id));
    }).catch(() => {});
  }, []);

  // Auto-select first branch of selected employee
  useEffect(() => {
    const emp = employees.find((e) => String(e.id) === userId);
    if (emp && emp.branch_ids.length && !branchId) {
      setBranchId(String(emp.branch_ids[0]));
    }
  }, [userId, employees, branchId]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!userId) return setError("کارمند را انتخاب کنید");
    if (!branchId) return setError("دفتر را انتخاب کنید");
    setBusy(true);
    try {
      await manualAttendance({
        user_id: Number(userId),
        branch_id: Number(branchId),
        work_date: date,
        check_in: checkIn,
        check_out: checkOut || null,
        work_description: description.trim() || null,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "خطا در ثبت حضور");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/35 backdrop-blur-sm p-4">
      <form onSubmit={submit} className="w-full max-w-lg space-y-5 glass-strong rounded-3xl p-7">
        <div>
          <h2 className="text-lg font-bold text-slate-900">ثبت دستی ورود / خروج</h2>
          <p className="text-sm text-slate-500">ثبت حضور کارمند توسط مدیر (بدون نیاز به GPS)</p>
        </div>
        {error && <Alert>{error}</Alert>}
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="کارمند">
            <Select value={userId} onChange={(e) => setUserId(e.target.value)}>
              <option value="">انتخاب کنید…</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>{e.full_name}</option>
              ))}
            </Select>
          </Field>
          <Field label="دفتر">
            <Select value={branchId} onChange={(e) => setBranchId(e.target.value)}>
              <option value="">انتخاب کنید…</option>
              {branches.map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </Select>
          </Field>
        </div>
        <Field label="تاریخ">
          <JalaliDateField value={date} onChange={setDate} />
        </Field>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="ساعت ورود">
            <Input type="time" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} required dir="ltr" />
          </Field>
          <Field label="ساعت خروج (اختیاری)">
            <Input type="time" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} dir="ltr" />
          </Field>
        </div>
        <Field label="شرح کار (اختیاری)">
          <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="شرح کار روز…" />
        </Field>
        {employees.length === 0 && <Empty>ابتدا کارمند تعریف کنید.</Empty>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" type="button" onClick={onClose}>انصراف</Button>
          <Button type="submit" disabled={busy}>{busy ? "در حال ثبت…" : "ثبت حضور"}</Button>
        </div>
      </form>
    </div>
  );
}
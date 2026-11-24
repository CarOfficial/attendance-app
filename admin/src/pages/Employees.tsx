import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError } from "../api";
import { Alert, Badge, Button, Card, ConfirmDialog, Empty, Field, Input, Table } from "../components/ui";
import type { Branch, Employee } from "../types";

export function EmployeesPage() {
  const [employees, setEmployees] = useState<Employee[] | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [resetting, setResetting] = useState<Employee | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [deleting, setDeleting] = useState<Employee | null>(null);
  const [force, setForce] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const branchName = (id: number) => branches.find((b) => b.id === id)?.name ?? `#${id}`;

  const attemptDelete = async () => {
    if (!deleting) return;
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await api(`/admin/employees/${deleting.id}${force ? "?force=true" : ""}`, { method: "DELETE" });
      setNotice(`حساب ${deleting.full_name} حذف شد.`);
      setDeleting(null);
      setForce(false);
      void load();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setForce(true);
        setDeleteError("این کارمند سابقه حضور یا مرخصی دارد. با تایید دوباره، حساب و همه سوابق او حذف می‌شود.");
      } else {
        setDeleteError(e instanceof ApiError ? e.message : "خطا در حذف کارمند");
      }
    } finally {
      setDeleteBusy(false);
    }
  };

  const load = () =>
    api<Employee[]>("/admin/employees")
      .then(setEmployees)
      .catch((e) => setError(e instanceof ApiError ? e.message : "خطا در دریافت کارمندان"));

  useEffect(() => {
    void load();
    api<Branch[]>("/admin/branches").then(setBranches).catch(() => {});
  }, []);

  const toggleActive = async (emp: Employee) => {
    setError(null);
    try {
      await api(`/admin/employees/${emp.id}`, { method: "PATCH", body: { is_active: !emp.is_active } });
      void load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "خطا");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-royal-gradient">کارمندان</h1>
          <p className="mt-1 text-sm text-slate-500">مدیریت حساب‌ها، دفاتر مجاز و رمز عبور</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="جستجوی نام یا نام کاربری…"
            className="w-56"
          />
          <Button onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "بستن فرم" : "+ کارمند جدید"}
          </Button>
        </div>
      </div>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      {showCreate && (
        <CreateEmployeeForm
          branches={branches}
          onCreated={(name) => {
            setShowCreate(false);
            setNotice(`حساب ${name} ساخته شد. کارمند باید در اولین ورود رمز را تغییر دهد.`);
            void load();
          }}
        />
      )}

      <Card>
        {employees === null ? (
          <Empty>در حال بارگذاری…</Empty>
        ) : employees.length === 0 ? (
          <Empty>هنوز کارمندی ثبت نشده است.</Empty>
        ) : (
          <Table head={["نام", "نام کاربری", "دفاتر مجاز", "وضعیت", "عملیات"]}>
            {employees
              .filter((emp) => {
                const q = search.trim();
                if (!q) return true;
                return emp.full_name.includes(q) || emp.username.includes(q.toLowerCase());
              })
              .map((emp) => (
              <tr key={emp.id}>
                <td className="px-4 py-3 font-medium text-slate-800">{emp.full_name}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-600" dir="ltr">{emp.username}</td>
                <td className="px-4 py-3 text-slate-600">
                  {emp.branch_ids.length === 0 ? <span className="text-amber-600">بدون دفتر</span>
                    : emp.branch_ids.map(branchName).join("، ")}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-1.5">
                    {emp.is_active ? <Badge tone="green">فعال</Badge> : <Badge tone="rose">غیرفعال</Badge>}
                    {emp.must_change_password && <Badge tone="amber">رمز موقت</Badge>}
                  </div>
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <div className="flex gap-3 text-sm">
                    <button onClick={() => setEditing(emp)} className="text-indigo-600 hover:underline">ویرایش</button>
                    <button onClick={() => setResetting(emp)} className="text-slate-600 hover:underline">بازنشانی رمز</button>
                    <button onClick={() => toggleActive(emp)} className={emp.is_active ? "text-amber-600 hover:underline" : "text-emerald-600 hover:underline"}>
                      {emp.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                    </button>
                    <button
                      onClick={() => {
                        setForce(false);
                        setDeleteError(null);
                        setDeleting(emp);
                      }}
                      className="text-rose-600 hover:underline"
                    >
                      حذف
                    </button>
                  </div>
                </td>
                </tr>
              ))}
          </Table>
        )}
      </Card>

      {deleting && (
        <ConfirmDialog
          title={`حذف حساب ${deleting.full_name}`}
          description={
            force
              ? "این کارمند سابقه دارد؛ با تایید، حساب و همه سوابق حضور و مرخصی او حذف می‌شود."
              : "حساب کاربری برای همیشه حذف می‌شود و ورود او به سامانه قطع می‌شود."
          }
          confirmLabel={force ? "حذف با سوابق" : "حذف حساب"}
          busy={deleteBusy}
          error={deleteError}
          onCancel={() => {
            setDeleting(null);
            setForce(false);
            setDeleteError(null);
          }}
          onConfirm={attemptDelete}
        />
      )}

      {editing && (
        <EditEmployeeDialog
          emp={editing}
          branches={branches}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            void load();
          }}
        />
      )}
      {resetting && (
        <ResetPasswordDialog
          emp={resetting}
          onClose={() => setResetting(null)}
          onDone={() => {
            setNotice(`رمز ${resetting.full_name} بازنشانی شد. در ورود بعدی باید رمز جدید بسازد.`);
            setResetting(null);
          }}
        />
      )}
    </div>
  );
}

function BranchCheckboxes({ branches, selected, onChange }: {
  branches: Branch[];
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  if (branches.length === 0) {
    return <p className="text-sm text-amber-600">ابتدا در بخش «دفاتر و موقعیت» یک دفتر تعریف کنید.</p>;
  }
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {branches.map((b) => (
        <label key={b.id} className="flex items-center gap-2 rounded-2xl glass px-3.5 py-2.5 text-sm">
          <input
            type="checkbox"
            checked={selected.includes(b.id)}
            onChange={(e) =>
              onChange(e.target.checked ? [...selected, b.id] : selected.filter((x) => x !== b.id))
            }
            className="h-4 w-4 accent-purple-700"
          />
          {b.name}
        </label>
      ))}
    </div>
  );
}

function CreateEmployeeForm({ branches, onCreated }: {
  branches: Branch[];
  onCreated: (name: string) => void;
}) {
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [branchIds, setBranchIds] = useState<number[]>([]);
  const [localError, setLocalError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (password.length < 8) return setLocalError("رمز اولیه باید حداقل ۸ کاراکتر باشد");
    setBusy(true);
    try {
      await api("/admin/employees", {
        method: "POST",
        body: { full_name: fullName, username: username.trim(), password, branch_ids: branchIds },
      });
      onCreated(fullName);
    } catch (err) {
      setLocalError(err instanceof ApiError ? err.message : "خطا در ساخت کارمند");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="کارمند جدید">
      <form onSubmit={submit} className="space-y-5">
        {localError && <Alert>{localError}</Alert>}
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="نام و نام خانوادگی">
            <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
          </Field>
          <Field label="نام کاربری" hint="حروف انگلیسی، عدد، نقطه، خط تیره یا زیرخط (۳ تا ۳۲ کاراکتر)">
            <Input value={username} onChange={(e) => setUsername(e.target.value)} required dir="ltr" />
          </Field>
          <Field label="رمز عبور اولیه" hint="کارمند بعداً خودش تغییرش می‌دهد">
            <Input type="text" value={password} onChange={(e) => setPassword(e.target.value)} required dir="ltr" />
          </Field>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">دفاتر مجاز برای ثبت حضور</p>
          <BranchCheckboxes branches={branches} selected={branchIds} onChange={setBranchIds} />
        </div>
        <div className="flex justify-end">
          <Button type="submit" disabled={busy}>{busy ? "در حال ساخت…" : "ساخت حساب"}</Button>
        </div>
      </form>
    </Card>
  );
}

function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/35 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-lg glass-strong rounded-3xl p-7" onClick={(e) => e.stopPropagation()}>
        <h2 className="mb-4 text-lg font-bold text-slate-900">{title}</h2>
        {children}
      </div>
    </div>
  );
}

function EditEmployeeDialog({ emp, branches, onClose, onSaved }: {
  emp: Employee;
  branches: Branch[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [fullName, setFullName] = useState(emp.full_name);
  const [branchIds, setBranchIds] = useState<number[]>(emp.branch_ids);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api(`/admin/employees/${emp.id}`, { method: "PATCH", body: { full_name: fullName, branch_ids: branchIds } });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "خطا");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog title={`ویرایش ${emp.username}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-5">
        {error && <Alert>{error}</Alert>}
        <Field label="نام و نام خانوادگی">
          <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required minLength={2} />
        </Field>
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">دفاتر مجاز</p>
          <BranchCheckboxes branches={branches} selected={branchIds} onChange={setBranchIds} />
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" type="button" onClick={onClose}>انصراف</Button>
          <Button type="submit" disabled={busy}>ذخیره</Button>
        </div>
      </form>
    </Dialog>
  );
}

function ResetPasswordDialog({ emp, onClose, onDone }: {
  emp: Employee;
  onClose: () => void;
  onDone: () => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 8) return setError("رمز باید حداقل ۸ کاراکتر باشد");
    setBusy(true);
    setError(null);
    try {
      await api(`/admin/employees/${emp.id}/reset-password`, { method: "POST", body: { new_password: password } });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "خطا");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog title={`بازنشانی رمز ${emp.full_name}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-5">
        <Alert tone="info">
          نشست‌های فعلی این کارمند بسته می‌شوند و در ورود بعدی باید رمز جدیدی انتخاب کند.
        </Alert>
        {error && <Alert>{error}</Alert>}
        <Field label="رمز موقت جدید">
          <Input value={password} onChange={(e) => setPassword(e.target.value)} required dir="ltr" />
        </Field>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" type="button" onClick={onClose}>انصراف</Button>
          <Button type="submit" variant="danger" disabled={busy}>بازنشانی</Button>
        </div>
      </form>
    </Dialog>
  );
}

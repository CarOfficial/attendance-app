import { useState } from "react";
import type { ButtonHTMLAttributes, FormEvent, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { toFa } from "../jalali";

/**
 * لوگوی سامانه «حضوریار». اگر فایل public/logo.png موجود نباشد،
 * به کاشی طلایی «ح» برمی‌گردد.
 */
export function BrandLogo({ className = "h-11 w-11 rounded-2xl", letterClass = "text-lg" }: {
  className?: string;
  letterClass?: string;
}) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className={`btn-gold flex items-center justify-center font-bold ${className} ${letterClass}`} aria-hidden>
        ح
      </div>
    );
  }
  return (
    <img
      src="/logo.png"
      alt="لوگوی حضوریار"
      onError={() => setFailed(true)}
      className={`object-contain ${className}`}
    />
  );
}

export function Card({ title, actions, children, className = "" }: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`glass rounded-3xl ${className}`}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-white/60 px-6 py-4">
          {title && (
            <h2 className="flex items-center gap-2 text-base font-semibold text-indigo-950">
              <span className="accent-line h-4 w-1 rounded-full" />
              {title}
            </h2>
          )}
          {actions}
        </header>
      )}
      <div className="p-6">{children}</div>
    </section>
  );
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "gold" | "secondary" | "danger" | "ghost" }) {
  const styles = {
    primary: "btn-royal",
    gold: "btn-gold",
    secondary: "bg-white/70 text-indigo-800 ring-1 ring-inset ring-indigo-200 backdrop-blur hover:bg-white disabled:text-slate-400",
    danger: "bg-gradient-to-br from-rose-500 to-rose-700 text-white shadow-lg shadow-rose-600/30 disabled:opacity-60",
    ghost: "text-indigo-800 hover:bg-indigo-100/60",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold transition duration-200 active:scale-[0.98] disabled:cursor-not-allowed ${styles} ${className}`}
    />
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-medium text-indigo-950/80">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

const inputCls =
  "block w-full rounded-2xl border border-purple-200/80 bg-purple-50/60 px-4 py-2.5 text-sm text-slate-900 shadow-inner shadow-purple-900/5 placeholder:text-slate-400 transition focus:border-purple-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-purple-500/15";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={`${inputCls} ${props.className ?? ""}`} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${inputCls} ${props.className ?? ""}`} />;
}

export function Badge({ tone = "slate", children }: {
  tone?: "slate" | "green" | "amber" | "rose" | "indigo";
  children: ReactNode;
}) {
  const tones = {
    slate: "bg-slate-100/80 text-slate-700 ring-slate-200",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    amber: "bg-gold-100 text-gold-700 ring-gold-200",
    rose: "bg-rose-50 text-rose-700 ring-rose-200",
    indigo: "bg-indigo-100/80 text-indigo-800 ring-indigo-200",
  }[tone];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${tones}`}>
      {children}
    </span>
  );
}

export function Alert({ tone = "error", children }: { tone?: "error" | "info" | "success"; children: ReactNode }) {
  const tones = {
    error: "border-rose-200/80 bg-rose-50/80 text-rose-700",
    info: "border-indigo-200/80 bg-indigo-50/80 text-indigo-900",
    success: "border-emerald-200/80 bg-emerald-50/80 text-emerald-800",
  }[tone];
  return <div className={`glass rounded-2xl border px-5 py-3.5 text-sm leading-6 ${tones}`}>{children}</div>;
}

const statGradients = {
  slate: "from-slate-500 to-slate-700",
  green: "from-emerald-400 to-emerald-600",
  rose: "from-rose-400 to-rose-600",
  indigo: "from-purple-500 to-indigo-800",
  amber: "from-gold-400 to-gold-600",
} as const;

export function Stat({ label, value, tone = "slate" }: {
  label: string;
  value: number | string;
  tone?: keyof typeof statGradients;
}) {
  return (
    <div className="glass group relative overflow-hidden rounded-3xl p-6">
      <div className={`absolute -top-10 -left-10 h-32 w-32 rounded-full bg-gradient-to-br ${statGradients[tone]} opacity-20 blur-2xl transition group-hover:opacity-35`} />
      <p className="relative text-sm font-medium text-slate-500">{label}</p>
      <p className={`relative mt-3 bg-gradient-to-br bg-clip-text text-4xl font-bold tabular-nums text-transparent ${statGradients[tone]}`}>
        {toFa(value)}
      </p>
    </div>
  );
}

export function Table({ head, children }: { head: string[]; children: ReactNode }) {
  return (
    <div className="scroll-thin overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-indigo-100/80">
            {head.map((h) => (
              <th key={h} className="whitespace-nowrap px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-indigo-900/60">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-indigo-100/60">{children}</tbody>
      </table>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-12 text-center text-sm text-slate-500">{children}</p>;
}

/** دیالوگ تایید عمومی برای کارهای حساس (حذف و…) */
export function ConfirmDialog({ title, description, confirmLabel = "حذف", busy = false, error, onCancel, onConfirm }: {
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/35 backdrop-blur-sm p-4" onClick={onCancel}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md space-y-5 glass-strong rounded-3xl p-7">
        <div>
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
          {description && <div className="mt-2 text-sm leading-6 text-slate-600">{description}</div>}
        </div>
        {error && <Alert>{error}</Alert>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" type="button" onClick={onCancel} disabled={busy}>انصراف</Button>
          <Button type="button" variant="danger" onClick={onConfirm} disabled={busy}>
            {busy ? "در حال انجام…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

/** دیالوگ مشترک تصمیم مدیر (تایید/رد) با یادداشت اختیاری */
export function DecisionDialog({ title, description, confirmLabel = "تایید", danger = false, busy = false, error, onCancel, onConfirm }: {
  title: string;
  description?: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  busy?: boolean;
  error?: string | null;
  onCancel: () => void;
  onConfirm: (note: string) => void;
}) {
  const [note, setNote] = useState("");
  const submit = (e: FormEvent) => {
    e.preventDefault();
    onConfirm(note.trim());
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-indigo-950/35 backdrop-blur-sm p-4" onClick={onCancel}>
      <form
        onSubmit={submit}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md space-y-5 glass-strong rounded-3xl p-7"
      >
        <div>
          <h2 className="text-lg font-bold text-slate-900">{title}</h2>
          {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
        </div>
        {error && <Alert>{error}</Alert>}
        <Field label="یادداشت مدیر" hint="اختیاری">
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            placeholder="در صورت نیاز دلیل تصمیم را بنویسید…"
            className="block w-full rounded-2xl border border-purple-200/80 bg-purple-50/60 px-4 py-2.5 text-sm text-slate-900 shadow-inner shadow-purple-900/5 placeholder:text-slate-400 transition focus:border-purple-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-purple-500/15"
          />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" type="button" onClick={onCancel} disabled={busy}>انصراف</Button>
          <Button type="submit" variant={danger ? "danger" : "primary"} disabled={busy}>
            {busy ? "در حال اعمال…" : confirmLabel}
          </Button>
        </div>
      </form>
    </div>
  );
}

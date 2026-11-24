import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`glass rounded-[1.75rem] p-5 ${className}`}>{children}</section>;
}

export function Button({ variant = "primary", className = "", ...props }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "gold" | "ghost" }) {
  const styles = {
    primary: "btn-royal",
    gold: "btn-gold",
    ghost: "text-indigo-800",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center rounded-2xl px-4 py-3.5 text-base font-semibold transition duration-200 active:scale-[0.98] disabled:cursor-not-allowed ${styles} ${className}`}
    />
  );
}

/** Wraps a control in a real <label> so the text is associated with the input. */
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-indigo-950/80">{label}</span>
      {children}
    </label>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`block w-full rounded-2xl border border-purple-200/80 bg-purple-50/60 px-4 py-3.5 text-base text-slate-900 shadow-inner shadow-purple-900/5 transition focus:border-purple-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-purple-500/15 ${props.className ?? ""}`}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`block w-full rounded-2xl border border-purple-200/80 bg-purple-50/60 px-4 py-3 text-base leading-7 text-slate-900 shadow-inner shadow-purple-900/5 transition focus:border-purple-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-purple-500/15 ${props.className ?? ""}`}
    />
  );
}

/** Small rounded label used for statuses and tags. */
export function Chip({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ring-inset ${className}`}
    >
      {children}
    </span>
  );
}

export function Alert({ tone = "error", children }: { tone?: "error" | "info" | "success"; children: ReactNode }) {
  const tones = {
    error: "border-rose-200/80 bg-rose-50/85 text-rose-700",
    info: "border-indigo-200/80 bg-indigo-50/85 text-indigo-900",
    success: "border-emerald-200/80 bg-emerald-50/85 text-emerald-800",
  }[tone];
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`glass rounded-2xl border px-5 py-3.5 text-sm leading-6 ${tones}`}>
      {children}
    </div>
  );
}

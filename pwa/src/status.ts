import type { ApprovalStatus, DayStatus, LateCheckoutStatus, RequestStatus } from "./types";

export interface StatusMeta {
  label: string;
  /** classes for a rounded chip (bg + text + ring) */
  chip: string;
  /** class for the small legend dot */
  dot: string;
}

/** برچسب و رنگ هر وضعیت روز (جدول §6 قرارداد) */
export const DAY_STATUS_META: Record<DayStatus, StatusMeta> = {
  present: { label: "حاضر", chip: "bg-emerald-50 text-emerald-700 ring-emerald-200", dot: "bg-emerald-500" },
  working: { label: "در حال کار", chip: "bg-sky-100 text-sky-700 ring-sky-200", dot: "bg-sky-500" },
  absent: { label: "غایب", chip: "bg-rose-50 text-rose-700 ring-rose-200", dot: "bg-rose-500" },
  incomplete: {
    label: "غایب (خروج ثبت نشده)",
    chip: "bg-orange-100 text-orange-700 ring-orange-200",
    dot: "bg-orange-500",
  },
  rejected: { label: "رد شده توسط مدیر", chip: "bg-red-100 text-red-700 ring-red-300", dot: "bg-red-500" },
  leave: { label: "مرخصی", chip: "bg-teal-100 text-teal-700 ring-teal-200", dot: "bg-teal-500" },
  pending_checkout: {
    label: "در انتظار تایید خروج",
    chip: "bg-gold-100 text-gold-700 ring-gold-200",
    dot: "bg-gold-500",
  },
  non_working: { label: "غیرکاری", chip: "bg-slate-100 text-slate-600 ring-slate-200", dot: "bg-slate-400" },
  future: { label: "پیش رو", chip: "bg-indigo-50 text-indigo-700 ring-indigo-200", dot: "bg-indigo-400" },
};

export function dayStatusMeta(status: string): StatusMeta {
  return DAY_STATUS_META[status as DayStatus] ?? {
    label: status,
    chip: "bg-slate-100 text-slate-600 ring-slate-200",
    dot: "bg-slate-400",
  };
}

/** درخواست‌های مرخصی و خروج فراموش‌شده */
export const REQUEST_STATUS_META: Record<RequestStatus, StatusMeta> = {
  pending: { label: "در انتظار تایید", chip: "bg-gold-100 text-gold-700 ring-gold-200", dot: "bg-gold-500" },
  approved: { label: "تایید شد", chip: "bg-emerald-50 text-emerald-700 ring-emerald-200", dot: "bg-emerald-500" },
  rejected: { label: "رد شد", chip: "bg-rose-50 text-rose-700 ring-rose-200", dot: "bg-rose-500" },
};

export const LATE_STATUS_META: Record<LateCheckoutStatus, StatusMeta> = {
  ...REQUEST_STATUS_META,
  expired: { label: "منقضی شد", chip: "bg-slate-100 text-slate-600 ring-slate-200", dot: "bg-slate-400" },
};

export function requestStatusMeta(status: string): StatusMeta {
  const all: Record<string, StatusMeta> = {
    pending: REQUEST_STATUS_META.pending,
    approved: REQUEST_STATUS_META.approved,
    rejected: REQUEST_STATUS_META.rejected,
    expired: LATE_STATUS_META.expired,
  };
  return all[status] ?? {
    label: status,
    chip: "bg-slate-100 text-slate-600 ring-slate-200",
    dot: "bg-slate-400",
  };
}

/** تصمیم مدیر روی رکورد حضور */
export const APPROVAL_META: Record<ApprovalStatus, StatusMeta> = {
  none: { label: "بدون تصمیم", chip: "bg-slate-100 text-slate-600 ring-slate-200", dot: "bg-slate-400" },
  approved: { label: "تایید شد", chip: "bg-emerald-50 text-emerald-700 ring-emerald-200", dot: "bg-emerald-500" },
  rejected: { label: "رد شد", chip: "bg-rose-50 text-rose-700 ring-rose-200", dot: "bg-rose-500" },
};

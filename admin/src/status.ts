import type { ApprovalStatus, DayStatus, LateCheckoutStatus, LeaveStatus } from "./types";

export type Tone = "slate" | "green" | "amber" | "rose" | "indigo";

export interface StatusLabel {
  label: string;
  tone: Tone;
}

/** برچسب‌های فارسی وضعیت‌های روز — قرارداد API بند §۲ */
export const DAY_STATUS: Record<DayStatus, StatusLabel> = {
  present: { label: "حاضر", tone: "green" },
  working: { label: "در حال کار", tone: "indigo" },
  absent: { label: "غایب", tone: "rose" },
  incomplete: { label: "غایب (خروج ثبت نشده)", tone: "rose" },
  rejected: { label: "رد شده توسط مدیر", tone: "rose" },
  leave: { label: "مرخصی", tone: "amber" },
  pending_checkout: { label: "در انتظار تایید خروج", tone: "amber" },
  non_working: { label: "غیرکاری", tone: "slate" },
  future: { label: "پیش رو", tone: "slate" },
};

export const APPROVAL_STATUS: Record<ApprovalStatus, StatusLabel> = {
  none: { label: "—", tone: "slate" },
  approved: { label: "تایید شد", tone: "green" },
  rejected: { label: "رد شد", tone: "rose" },
};

export const LEAVE_STATUS: Record<LeaveStatus, StatusLabel> = {
  pending: { label: "در انتظار", tone: "amber" },
  approved: { label: "تاییدشده", tone: "green" },
  rejected: { label: "رد شده", tone: "rose" },
};

export const LATE_STATUS: Record<LateCheckoutStatus, StatusLabel> = {
  pending: { label: "در انتظار", tone: "amber" },
  approved: { label: "تاییدشده", tone: "green" },
  rejected: { label: "رد شده", tone: "rose" },
  expired: { label: "منقضی", tone: "slate" },
};

/** نام روز هفته به فارسی از روی تاریخ میلادی «YYYY-MM-DD» */
export function weekdayName(isoDate: string): string {
  const names = ["یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"];
  const [y, m, d] = isoDate.split("-").map(Number);
  return names[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

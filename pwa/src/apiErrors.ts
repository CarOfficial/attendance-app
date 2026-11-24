import { formatJalaliDate } from "./jalali";

/**
 * The API returns English details. Map the known ones (contract §6) to Persian
 * for employees. Unknown messages are shown as-is.
 */

const REQUEST_STATUS_FA: Record<string, string> = {
  pending: "در انتظار",
  approved: "تاییدشده",
  rejected: "ردشده",
  expired: "منقضی",
};

function statusFa(status: string): string {
  return REQUEST_STATUS_FA[status] ?? status;
}

type Rule = { re: RegExp; fa: string | ((m: RegExpMatchArray) => string) };

const RULES: Rule[] = [
  // ---------- auth ----------
  { re: /^Invalid username or password$/, fa: "نام کاربری یا رمز عبور اشتباه است" },
  {
    re: /^Account temporarily locked/,
    fa: "حساب به دلیل تلاش‌های ناموفق قفل شد. ۱۵ دقیقه دیگر دوباره امتحان کنید",
  },
  { re: /^Password change required$/, fa: "ابتدا رمز عبور خود را تغییر دهید" },
  { re: /^Current password is incorrect$/, fa: "رمز عبور فعلی اشتباه است" },
  {
    re: /^New password must be different from the current one$/,
    fa: "رمز جدید باید با رمز فعلی متفاوت باشد",
  },
  { re: /^Invalid or expired token$/, fa: "نشست شما منقضی شده؛ دوباره وارد شوید" },
  { re: /^Admin only$/, fa: "فقط مدیر" },

  // ---------- location ----------
  {
    re: /^You are outside the allowed area\. Nearest branch: (.+) \(~(\d+) m\)/,
    fa: (m) => `خارج از محدوده‌ی مجاز هستید. نزدیک‌ترین شعبه: ${m[1]} (حدود ${toFa(m[2])} متر فاصله)`,
  },
  {
    re: /^GPS accuracy too low/,
    fa: "دقت موقعیت مکانی پایین است؛ به فضای باز بروید و دوباره تلاش کنید",
  },
  { re: /^No active branch is assigned to you$/, fa: "شعبه‌ای برای شما تعریف نشده است" },
  {
    re: /^You must be (.+) to check out \(~(\d+) m away\)/,
    fa: (m) => `برای ثبت خروج باید در محدوده‌ی شعبه ${m[1]} باشید (حدود ${toFa(m[2])} متر فاصله)`,
  },

  // ---------- attendance ----------
  { re: /^You have already checked in today$/, fa: "امروز قبلاً ثبت ورود کرده‌اید" },
  { re: /^No open check-in found$/, fa: "ثبت ورود بازی وجود ندارد" },
  {
    re: /^Check-out for (\d{4}-\d{2}-\d{2}) was never recorded/,
    fa: (m) => `خروج ${formatJalaliDate(m[1])} ثبت نشده؛ از بخش «فراموشی خروج» اقدام کنید`,
  },
  { re: /^There is an open check-in/, fa: "ثبت ورود روز قبل بدون خروج باقی مانده است. لطفاً با مدیر تماس بگیرید." },
  {
    re: /^A short description of today's work is required$/,
    fa: "شرح کار روزانه الزامی است",
  },
  { re: /^A short description of the work is required$/, fa: "شرح کار الزامی است" },
  { re: /^You have an approved leave for today$/, fa: "امروز مرخصی تاییدشده دارید" },

  // ---------- forgotten check-out ----------
  { re: /^work_date must be a past day$/, fa: "فقط می‌توان برای روزهای گذشته درخواست ثبت کرد" },
  {
    re: /^The 24-hour window for reporting this check-out has passed$/,
    fa: "مهلت ۲۴ ساعته ثبت خروج تمام شده است",
  },
  { re: /^That day is not a working day$/, fa: "آن روز، روز کاری نیست" },
  {
    re: /^No check-in found for (\d{4}-\d{2}-\d{2})$/,
    fa: (m) => `برای ${formatJalaliDate(m[1])} ثبت ورودی وجود ندارد`,
  },
  { re: /^Check-out is already recorded for that day$/, fa: "خروج آن روز قبلاً ثبت شده است" },
  {
    re: /^A request for that day already exists \(([^)]+)\)$/,
    fa: (m) => `برای آن روز درخواستی ثبت شده است (${statusFa(m[1])})`,
  },
  { re: /^Check-out time must be after check-in$/, fa: "ساعت خروج باید بعد از ساعت ورود باشد" },
  { re: /^Check-out time cannot be in the future$/, fa: "ساعت خروج نمی‌تواند در آینده باشد" },
  { re: /^check_out_time must be HH:MM$/, fa: "ساعت خروج را به‌درستی وارد کنید" },
  {
    re: /^Request is already ([^ ]+)$/,
    fa: (m) => `درخواست قبلاً بررسی شده است (${statusFa(m[1])})`,
  },
  {
    re: /^This day has no check-out; use the forgotten check-out request instead$/,
    fa: "این روز خروج ندارد؛ ابتدا خروج فراموش‌شده را ثبت کنید",
  },

  // ---------- leaves ----------
  { re: /^Leave request is already ([^ ]+)$/, fa: (m) => `درخواست مرخصی قبلاً بررسی شده است (${statusFa(m[1])})` },
  { re: /^Leave request already exists$/, fa: "برای این تاریخ‌ها درخواست مرخصی ثبت شده است" },
  { re: /^start_date must not be after end_date$/, fa: "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد" },
  { re: /^Leave cannot start more than 3 days in the past$/, fa: "مرخصی حداکثر برای ۳ روز گذشته قابل ثبت است" },
  { re: /^Leave range is too long$/, fa: "بازه مرخصی بیش از حد طولانی است" },
  {
    re: /^You already have a pending or approved leave for these dates$/,
    fa: "برای این تاریخ‌ها مرخصی در انتظار یا تاییدشده دارید",
  },
  { re: /^Reason is too short$/, fa: "دلیل مرخصی را کامل بنویسید" },

  // ---------- queries / records ----------
  { re: /^from_date must be before to_date$/, fa: "تاریخ شروع باید قبل از تاریخ پایان باشد" },
  { re: /^Date range too large/, fa: "بازه تاریخ بیش از حد طولانی است (حداکثر ۴۰۰ روز)" },
  { re: /^Employee not found$/, fa: "کارمند پیدا نشد" },
  { re: /^Leave request not found$/, fa: "درخواست مرخصی پیدا نشد" },
  { re: /^Request not found$/, fa: "درخواست پیدا نشد" },
  { re: /^Attendance record not found$/, fa: "رکورد حضور و غیاب پیدا نشد" },
  { re: /^Username already exists$/, fa: "این نام کاربری قبلاً ثبت شده است" },
  { re: /^One or more branch ids are invalid$/, fa: "یک یا چند شعبه انتخاب‌شده معتبر نیست" },
  { re: /^Branch not found$/, fa: "شعبه پیدا نشد" },
];

export function toPersianMessage(detail: string): string {
  for (const rule of RULES) {
    const match = detail.match(rule.re);
    if (match) return typeof rule.fa === "function" ? rule.fa(match) : rule.fa;
  }
  return detail;
}

function toFa(v: string): string {
  return v.replace(/\d/g, (n) => "۰۱۲۳۴۵۶۷۸۹"[Number(n)]);
}

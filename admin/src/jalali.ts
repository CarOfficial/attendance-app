import jalaali from "jalaali-js";

const FA_MONTHS = [
  "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
];

const TZ = "Asia/Tehran";

/** "YYYY-MM-DD" (Gregorian) -> "۱۴۰۵/۰۸/۱۰" */
export function formatJalaliDate(isoDate: string): string {
  const { jy, jm, jd } = jalaliParts(isoDate);
  return `${toFa(jy)}/${toFa(String(jm).padStart(2, "0"))}/${toFa(String(jd).padStart(2, "0"))}`;
}

/** Gregorian "YYYY-MM-DD" -> {jy, jm, jd} */
export function jalaliParts(isoDate: string): { jy: number; jm: number; jd: number } {
  const [gy, gm, gd] = isoDate.split("-").map(Number);
  return jalaali.toJalaali(gy, gm, gd);
}

/** Today's Jalali date in Tehran as "۱۴۰۵/۰۸/۱۰" */
export function todayJalali(): string {
  return formatJalaliDate(todayIso());
}

/** Jalali y/m/d -> Gregorian "YYYY-MM-DD" */
export function jalaliToIso(jy: number, jm: number, jd: number): string {
  const { gy, gm, gd } = jalaali.toGregorian(jy, jm, jd);
  return `${String(gy).padStart(4, "0")}-${String(gm).padStart(2, "0")}-${String(gd).padStart(2, "0")}`;
}

/**
 * Accepts a typed Jalali date ("۱۴۰۵/۰۸/۱۰", "1405/8/10" or "1405-08-10") and returns
 * Gregorian "YYYY-MM-DD", or null when the text is not a real Jalali date.
 */
export function parseJalaliDate(text: string): string | null {
  const ascii = String(text).replace(/[۰-۹]/g, (d) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(d)));
  const parts = ascii
    .trim()
    .replace(/[-.]/g, "/")
    .split("/")
    .filter((p) => p !== "");
  if (parts.length !== 3) return null;
  const [jy, jm, jd] = parts.map(Number);
  if (![jy, jm, jd].every(Number.isInteger)) return null;
  if (jy < 1200 || jy > 1600 || jm < 1 || jm > 12 || jd < 1 || jd > 31) return null;
  if (!jalaali.isValidJalaaliDate(jy, jm, jd)) return null;
  return jalaliToIso(jy, jm, jd);
}

/** Number of days in a Jalali month (۱ تا ۱۲). */
export function jalaliMonthLength(jy: number, jm: number): number {
  return jalaali.jalaaliMonthLength(jy, jm);
}

/** Saturday-first weekday index of a Gregorian "YYYY-MM-DD" (0 = شنبه … 6 = جمعه). */
export function weekdayIndex(isoDate: string): number {
  const [y, m, d] = isoDate.split("-").map(Number);
  return (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 1) % 7;
}

export function jalaliMonthName(isoDate: string): string {
  const [gy, gm, gd] = isoDate.split("-").map(Number);
  return FA_MONTHS[jalaali.toJalaali(gy, gm, gd).jm - 1];
}

/** ISO datetime (UTC from API) -> "HH:MM" in Tehran time */
export function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const t = new Date(iso).toLocaleTimeString("fa-IR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: TZ,
  });
  return t;
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const day = d.toLocaleDateString("en-CA", { timeZone: TZ }); // YYYY-MM-DD
  return `${formatJalaliDate(day)} ${formatTime(iso)}`;
}

/** Today's date in Tehran as "YYYY-MM-DD" */
export function todayIso(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: TZ });
}

export function addDaysIso(iso: string, days: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d + days));
  return dt.toISOString().slice(0, 10);
}

export function toFa(v: number | string): string {
  return String(v).replace(/\d/g, (n) => "۰۱۲۳۴۵۶۷۸۹"[Number(n)]);
}

/** 10.25 -> "۱۰٫۳ ساعت" (Persian digits and decimal separator). */
export function formatHours(value: number | null): string {
  if (value === null || Number.isNaN(value)) return "—";
  return `${toFa(value.toFixed(1)).replace(".", "٫")} ساعت`;
}

import jalaali from "jalaali-js";

const FA_MONTHS = [
  "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
];

const TZ = "Asia/Tehran";

/** "YYYY-MM-DD" (Gregorian) -> "۱۴۰۵/۰۸/۱۰" */
export function formatJalaliDate(isoDate: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return "—";
  const [gy, gm, gd] = isoDate.split("-").map(Number);
  const { jy, jm, jd } = jalaali.toJalaali(gy, gm, gd);
  return `${toFa(jy)}/${toFa(String(jm).padStart(2, "0"))}/${toFa(String(jd).padStart(2, "0"))}`;
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

const FA_WEEKDAYS = ["یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه"];

/** "YYYY-MM-DD" -> نام روز هفته به فارسی (شنبه تا جمعه) */
export function weekDayName(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  return FA_WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
}

/** Saturday of the week containing the given date (Iranian week starts on شنبه). */
export function weekStartIso(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map(Number);
  const dow = new Date(Date.UTC(y, m - 1, d)).getUTCDay(); // 0=Sunday … 6=Saturday
  return addDaysIso(isoDate, -((dow - 6 + 7) % 7));
}

/** 7.5 -> "۷٫۵ ساعت" */
export function formatHours(value: number): string {
  const raw = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return `${toFa(raw).replace(".", "٫")} ساعت`;
}

/** "17:00" -> "۱۷:۰۰" */
export function toFaTime(hhmm: string): string {
  return toFa(hhmm);
}

export function toFa(v: number | string): string {
  return String(v).replace(/\d/g, (n) => "۰۱۲۳۴۵۶۷۸۹"[Number(n)]);
}

import { useEffect, useState } from "react";
import {
  formatJalaliDate,
  jalaliMonthLength,
  jalaliParts,
  jalaliToIso,
  parseJalaliDate,
  toFa,
  todayIso,
  weekdayIndex,
} from "../jalali";

const MONTHS = [
  "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
];

/** شنبه … جمعه */
const WEEKDAYS = ["ش", "ی", "د", "س", "چ", "پ", "ج"];

const fieldCls =
  "block w-full rounded-2xl border border-purple-200/80 bg-purple-50/60 px-4 py-2.5 text-sm text-slate-900 shadow-inner shadow-purple-900/5 placeholder:text-slate-400 transition focus:border-purple-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-purple-500/15";

/**
 * ورودی تاریخ شمسی: تایپ دستی («۱۴۰۵/۰۸/۱۰») یا انتخاب از تقویم شمسی.
 * مقدار خروجی همیشه تاریخ میلادی «YYYY-MM-DD» است تا با API هم‌خوان بماند.
 */
export function JalaliDateField({
  value,
  onChange,
  className = "",
}: {
  value: string;
  onChange: (isoDate: string) => void;
  className?: string;
}) {
  const [text, setText] = useState(value ? formatJalaliDate(value) : "");
  const [open, setOpen] = useState(false);
  const [invalid, setInvalid] = useState(false);

  // Keep the visible text in sync when the value changes from outside (e.g. "هفته قبل").
  useEffect(() => {
    setText(value ? formatJalaliDate(value) : "");
    setInvalid(false);
  }, [value]);

  const base = (value || todayIso()).slice(0, 10);
  const parts = jalaliParts(base);
  const [cursor, setCursor] = useState({ jy: parts.jy, jm: parts.jm });

  const openCalendar = () => {
    const p = jalaliParts(base);
    setCursor({ jy: p.jy, jm: p.jm });
    setOpen(true);
  };

  const typeDate = (raw: string) => {
    setText(raw);
    if (raw.trim() === "") {
      setInvalid(false);
      return;
    }
    const iso = parseJalaliDate(raw);
    if (iso) {
      setInvalid(false);
      if (iso !== value) onChange(iso);
    } else {
      setInvalid(true);
    }
  };

  const shiftMonth = (delta: number) => {
    setCursor((cur) => {
      const total = (cur.jy * 12 + (cur.jm - 1)) + delta;
      return { jy: Math.floor(total / 12), jm: (total % 12) + 1 };
    });
  };

  const firstWeekday = weekdayIndex(jalaliToIso(cursor.jy, cursor.jm, 1));
  const length = jalaliMonthLength(cursor.jy, cursor.jm);
  const cells: (number | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div className={`relative ${className}`}>
      <div className="flex gap-2">
        <input
          value={text}
          onChange={(e) => typeDate(e.target.value)}
          dir="ltr"
          inputMode="numeric"
          placeholder="۱۴۰۵/۰۸/۱۰"
          aria-label="تاریخ شمسی"
          className={`${fieldCls} ${invalid ? "border-rose-400 bg-rose-50/60" : ""}`}
        />
        <button
          type="button"
          onClick={() => (open ? setOpen(false) : openCalendar())}
          title="انتخاب از تقویم شمسی"
          aria-label="تقویم شمسی"
          className="shrink-0 rounded-2xl border border-purple-200/80 bg-white/80 px-3 text-base text-indigo-700 transition hover:border-purple-400 hover:bg-white"
        >
          📅
        </button>
      </div>
      {invalid && (
        <p className="mt-1 text-xs text-rose-600">تاریخ شمسی معتبر نیست؛ نمونه: ۱۴۰۵/۰۸/۱۰</p>
      )}

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute left-0 z-40 mt-2 w-72 rounded-3xl border border-purple-200/80 bg-white p-4 shadow-2xl shadow-indigo-900/20">
            <div className="mb-3 flex items-center justify-between">
              <button
                type="button"
                onClick={() => shiftMonth(-1)}
                className="rounded-xl px-2 py-1 text-indigo-700 hover:bg-purple-50"
                aria-label="ماه قبل"
              >
                ›
              </button>
              <p className="text-sm font-semibold text-indigo-950">
                {MONTHS[cursor.jm - 1]} {toFa(cursor.jy)}
              </p>
              <button
                type="button"
                onClick={() => shiftMonth(1)}
                className="rounded-xl px-2 py-1 text-indigo-700 hover:bg-purple-50"
                aria-label="ماه بعد"
              >
                ‹
              </button>
            </div>

            <div className="grid grid-cols-7 gap-1 text-center text-[11px] font-medium text-indigo-900/50">
              {WEEKDAYS.map((d) => (
                <span key={d} className="py-1">{d}</span>
              ))}
            </div>

            <div className="mt-1 grid grid-cols-7 gap-1">
              {cells.map((day, index) => {
                if (day === null) return <span key={`empty-${index}`} />;
                const iso = jalaliToIso(cursor.jy, cursor.jm, day);
                const selected = iso === value;
                const isToday = iso === todayIso();
                return (
                  <button
                    key={iso}
                    type="button"
                    onClick={() => {
                      onChange(iso);
                      setOpen(false);
                    }}
                    className={`rounded-xl py-1.5 text-sm tabular-nums transition ${
                      selected
                        ? "btn-royal"
                        : isToday
                          ? "bg-gold-100 text-gold-700 ring-1 ring-inset ring-gold-200"
                          : "text-indigo-900 hover:bg-purple-50"
                    }`}
                  >
                    {toFa(day)}
                  </button>
                );
              })}
            </div>

            <div className="mt-3 flex items-center justify-between border-t border-indigo-100 pt-3">
              <button
                type="button"
                onClick={() => {
                  onChange(todayIso());
                  setOpen(false);
                }}
                className="text-xs font-medium text-indigo-700 hover:underline"
              >
                امروز
              </button>
              <span className="text-[11px] text-slate-500">{formatJalaliDate(todayIso())}</span>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

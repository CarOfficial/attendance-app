import { useEffect, useState } from "react";
import { formatJalaliDate, parseJalaliDate } from "../jalali";
import { Input } from "./ui";

/**
 * ورودی تاریخ شمسی برای PWA؛ تایپ «۱۴۰۵/۰۸/۱۰» یا «1405-8-10» را می‌پذیرد و
 * مقدار میلادی «YYYY-MM-DD» را به والد می‌دهد.
 */
export function JalaliDateInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (isoDate: string) => void;
}) {
  const [text, setText] = useState(value ? formatJalaliDate(value) : "");
  const [invalid, setInvalid] = useState(false);

  useEffect(() => {
    setText(value ? formatJalaliDate(value) : "");
    setInvalid(false);
  }, [value]);

  const change = (raw: string) => {
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

  return (
    <div>
      <Input
        value={text}
        onChange={(e) => change(e.target.value)}
        placeholder="۱۴۰۵/۰۸/۱۰"
        inputMode="numeric"
        dir="ltr"
        aria-label="تاریخ شمسی"
        aria-invalid={invalid}
        className={invalid ? "!border-rose-400 !bg-rose-50/60" : ""}
      />
      {invalid ? (
        <p className="mt-1 text-[11px] text-rose-600">تاریخ شمسی معتبر نیست؛ نمونه: ۱۴۰۵/۰۸/۱۰</p>
      ) : (
        value && <p className="mt-1 text-[11px] text-indigo-900/55">{formatJalaliDate(value)}</p>
      )}
    </div>
  );
}

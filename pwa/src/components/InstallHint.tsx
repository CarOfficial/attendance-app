import { useState } from "react";
import { isIosSafari, isStandalone } from "../install";
import { Card } from "./ui";

/**
 * iOS does not show an install prompt. Explain how to add the app to the home screen.
 * Hidden once installed or when dismissed.
 */
export function InstallHint() {
  const [dismissed, setDismissed] = useState(() => localStorage.getItem("install_hint_dismissed") === "1");
  if (dismissed || isStandalone() || !isIosSafari()) return null;

  return (
    <Card className="border-indigo-200 bg-indigo-50/60">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2 text-sm leading-6 text-slate-700">
          <p className="font-semibold text-indigo-900">نصب روی صفحه‌ی اصلی iPhone</p>
          <ol className="list-decimal space-y-1 pr-5">
            <li>در Safari، دکمه‌ی اشتراک‌گذاری <span dir="ltr">⬆</span> را بزنید.</li>
            <li>گزینه‌ی «Add to Home Screen» یا «افزودن به صفحه‌ی اصلی» را انتخاب کنید.</li>
            <li>برنامه را از صفحه‌ی اصلی باز کنید. موقعیت مکانی را همیشه با این روش باز کنید.</li>
          </ol>
        </div>
        <button
          onClick={() => {
            localStorage.setItem("install_hint_dismissed", "1");
            setDismissed(true);
          }}
          className="shrink-0 text-sm text-slate-500"
          aria-label="بستن"
        >
          ✕
        </button>
      </div>
    </Card>
  );
}

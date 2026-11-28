import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api";
import { getCurrentFix, LocationError } from "../location";
import { toPersianMessage } from "../apiErrors";
import { requestStatusMeta } from "../status";
import { addDaysIso, formatJalaliDate, formatTime, todayIso, toFa, toFaTime } from "../jalali";
import { Alert, Button, Card, Chip, Field, Input, TextArea } from "../components/ui";
import { JalaliDateInput } from "../components/JalaliDateInput";
import type { HourlyLeaveOut, LateCheckoutOut, LeaveOut } from "../types";

/** درخواست مرخصی + ثبت خروج فراموش‌شده (حداکثر ۲۴ ساعت). */
export function RequestsPage() {
  const [leaves, setLeaves] = useState<LeaveOut[]>([]);
  const [hourly, setHourly] = useState<HourlyLeaveOut[]>([]);
  const [lates, setLates] = useState<LateCheckoutOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const [l, h, c] = await Promise.all([
        api<LeaveOut[]>("/leaves/mine"),
        api<HourlyLeaveOut[]>("/leaves/hourly/mine"),
        api<LateCheckoutOut[]>("/attendance/late-checkouts"),
      ]);
      setLeaves(l);
      setHourly(h);
      setLates(c);
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? toPersianMessage(e.message) : "دریافت درخواست‌ها ناموفق بود.");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return (
    <div className="space-y-5">
      <header className="px-1">
        <h1 className="text-xl font-bold text-indigo-950">درخواست‌ها</h1>
        <p className="mt-1 text-sm text-indigo-900/60">مرخصی و ثبت خروج فراموش‌شده</p>
      </header>

      {error && <Alert>{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <LeaveSection
        leaves={leaves}
        onChanged={async (msg) => {
          setNotice(msg);
          await reload();
        }}
      />

      <HourlyLeaveSection
        hourly={hourly}
        onChanged={async (msg) => {
          setNotice(msg);
          await reload();
        }}
      />

      <ForgottenCheckoutSection
        lates={lates}
        onChanged={async (msg) => {
          setNotice(msg);
          await reload();
        }}
      />
    </div>
  );
}

function LeaveSection({
  leaves,
  onChanged,
}: {
  leaves: LeaveOut[];
  onChanged: (message: string) => Promise<void>;
}) {
  const [start, setStart] = useState(todayIso());
  const [end, setEnd] = useState(todayIso());
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const submit = async () => {
    setFormError(null);
    if (reason.trim().length < 3) {
      setFormError("دلیل مرخصی را کامل بنویسید.");
      return;
    }
    if (end < start) {
      setFormError("تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد.");
      return;
    }
    setBusy(true);
    try {
      await api("/leaves", {
        method: "POST",
        body: { start_date: start, end_date: end, reason: reason.trim() },
      });
      setReason("");
      await onChanged("درخواست مرخصی ثبت شد و در انتظار تایید مدیر است.");
    } catch (e) {
      setFormError(e instanceof ApiError ? toPersianMessage(e.message) : "ثبت درخواست مرخصی ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <h2 className="text-base font-bold text-indigo-950">درخواست مرخصی</h2>
      <p className="mt-1 text-xs leading-5 text-indigo-900/60">
        مرخصی فقط پس از تایید مدیر اعمال می‌شود.
      </p>

      <div className="mt-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="از تاریخ">
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} dir="ltr" />
          </Field>
          <Field label="تا تاریخ">
            <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} dir="ltr" />
          </Field>
        </div>
        <p className="text-[11px] text-indigo-900/55">
          {formatJalaliDate(start)} تا {formatJalaliDate(end)}
        </p>
        <Field label="دلیل مرخصی">
          <TextArea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} placeholder="مثلاً: مرخصی استحقاقی" />
        </Field>
        {formError && <Alert>{formError}</Alert>}
        <Button onClick={submit} disabled={busy} className="w-full">
          {busy ? "در حال ارسال…" : "ارسال درخواست مرخصی"}
        </Button>
      </div>

      {leaves.length > 0 && (
        <div className="mt-6 space-y-2.5">
          <p className="text-xs font-medium text-indigo-900/60">درخواست‌های من</p>
          {leaves.map((leave) => {
            const meta = requestStatusMeta(leave.status);
            return (
              <div key={leave.id} className="rounded-2xl bg-white/60 p-3.5 ring-1 ring-white/80">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-indigo-950">
                    {formatJalaliDate(leave.start_date)} تا {formatJalaliDate(leave.end_date)}
                  </p>
                  <Chip className={meta.chip}>{meta.label}</Chip>
                </div>
                <p className="mt-1.5 text-xs leading-6 text-indigo-900/70">{leave.reason}</p>
                {leave.decision_note && (
                  <p className="mt-1 text-[11px] text-indigo-900/55">یادداشت مدیر: {leave.decision_note}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

/** "10:30" -> 10.5 ; null when the text is not HH:MM. */
function hourValue(text: string): number | null {
  const match = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(text.trim());
  if (!match) return null;
  return Number(match[1]) + Number(match[2]) / 60;
}

/** 10.5 -> «۱۰:۳۰» */
function hourLabel(hour: number): string {
  const h = Math.floor(hour);
  const m = Math.round((hour - h) * 60);
  return toFa(`${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`);
}

function HourlyLeaveSection({
  hourly,
  onChanged,
}: {
  hourly: HourlyLeaveOut[];
  onChanged: (message: string) => Promise<void>;
}) {
  const [date, setDate] = useState(todayIso());
  const [from, setFrom] = useState("10:00");
  const [to, setTo] = useState("12:00");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const submit = async () => {
    setFormError(null);
    const start = hourValue(from);
    const end = hourValue(to);
    if (start === null || end === null) {
      setFormError("ساعت را به شکل ۱۰:۳۰ وارد کنید.");
      return;
    }
    if (start >= end) {
      setFormError("ساعت پایان باید بعد از ساعت شروع باشد.");
      return;
    }
    if (reason.trim().length < 3) {
      setFormError("دلیل مرخصی را کامل بنویسید.");
      return;
    }
    setBusy(true);
    try {
      await api("/leaves/hourly", {
        method: "POST",
        body: { date, start_hour: start, end_hour: end, reason: reason.trim() },
      });
      setReason("");
      await onChanged("درخواست مرخصی ساعتی ثبت شد و در انتظار تایید مدیر است.");
    } catch (e) {
      setFormError(e instanceof ApiError ? toPersianMessage(e.message) : "ثبت مرخصی ساعتی ناموفق بود.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <h2 className="text-base font-bold text-indigo-950">درخواست مرخصی ساعتی</h2>
      <p className="mt-1 text-xs leading-5 text-indigo-900/60">
        چند ساعت مرخصی در یک روز (مثلاً مراجعه به پزشک). پس از تایید مدیر اعمال می‌شود.
      </p>

      <div className="mt-4 space-y-3">
        <Field label="تاریخ (شمسی)">
          <JalaliDateInput value={date} onChange={setDate} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="از ساعت">
            <Input type="time" value={from} onChange={(e) => setFrom(e.target.value)} dir="ltr" />
          </Field>
          <Field label="تا ساعت">
            <Input type="time" value={to} onChange={(e) => setTo(e.target.value)} dir="ltr" />
          </Field>
        </div>
        <Field label="دلیل">
          <TextArea value={reason} onChange={(e) => setReason(e.target.value)} rows={2} placeholder="مثلاً: مراجعه به پزشک" />
        </Field>
        {formError && <Alert>{formError}</Alert>}
        <Button onClick={submit} disabled={busy} className="w-full">
          {busy ? "در حال ارسال…" : "ارسال درخواست مرخصی ساعتی"}
        </Button>
      </div>

      {hourly.length > 0 && (
        <div className="mt-6 space-y-2.5">
          <p className="text-xs font-medium text-indigo-900/60">مرخصی‌های ساعتی من</p>
          {hourly.map((leave) => {
            const meta = requestStatusMeta(leave.status);
            return (
              <div key={leave.id} className="rounded-2xl bg-white/60 p-3.5 ring-1 ring-white/80">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-indigo-950">
                    {formatJalaliDate(leave.date)} · {hourLabel(leave.start_hour)} تا {hourLabel(leave.end_hour)}
                  </p>
                  <Chip className={meta.chip}>{meta.label}</Chip>
                </div>
                <p className="mt-1.5 text-xs leading-6 text-indigo-900/70">{leave.reason}</p>
                {leave.decision_note && (
                  <p className="mt-1 text-[11px] text-indigo-900/55">یادداشت مدیر: {leave.decision_note}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

function ForgottenCheckoutSection({
  lates,
  onChanged,
}: {
  lates: LateCheckoutOut[];
  onChanged: (message: string) => Promise<void>;
}) {
  const [workDate, setWorkDate] = useState(() => addDaysIso(todayIso(), -1));
  const [time, setTime] = useState("17:00");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const submit = async () => {
    setFormError(null);
    if (description.trim().length < 3) {
      setFormError("شرح کار الزامی است.");
      return;
    }
    setBusy(true);
    try {
      const fix = await getCurrentFix();
      await api("/attendance/late-checkout", {
        method: "POST",
        body: {
          work_date: workDate,
          check_out_time: time,
          latitude: fix.latitude,
          longitude: fix.longitude,
          accuracy_m: fix.accuracy_m,
          description: description.trim(),
        },
      });
      setDescription("");
      await onChanged("درخواست ثبت خروج ارسال شد و در انتظار تایید مدیر است.");
    } catch (e) {
      const message = e instanceof LocationError ? e.message
        : e instanceof ApiError ? toPersianMessage(e.message)
        : "ثبت درخواست ناموفق بود.";
      setFormError(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <h2 className="text-base font-bold text-indigo-950">فراموشی ثبت خروج</h2>
      <p className="mt-1 text-xs leading-6 text-indigo-900/60">
        اگر خروج دیروز را ثبت نکرده‌اید، تا ۲۴ ساعت با حضور در محل کار می‌توانید آن را ثبت کنید. این درخواست باید
        توسط مدیر تایید شود؛ در غیر این صورت آن روز غایب محسوب می‌شود.
      </p>

      <div className="mt-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <Field label="تاریخ روز گذشته">
            <Input type="date" value={workDate} onChange={(e) => setWorkDate(e.target.value)} dir="ltr" />
          </Field>
          <Field label="ساعت خروج">
            <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} dir="ltr" />
          </Field>
        </div>
        <p className="text-[11px] text-indigo-900/55">
          {formatJalaliDate(workDate)} ساعت {toFaTime(time)}
        </p>
        <Field label="شرح کارهای آن روز">
          <TextArea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="کارهایی که آن روز انجام دادید"
          />
        </Field>
        {formError && <Alert>{formError}</Alert>}
        <Button variant="gold" onClick={submit} disabled={busy} className="w-full">
          {busy ? "در حال دریافت موقعیت…" : "ثبت درخواست با موقعیت فعلی"}
        </Button>
      </div>

      {lates.length > 0 && (
        <div className="mt-6 space-y-2.5">
          <p className="text-xs font-medium text-indigo-900/60">درخواست‌های خروج</p>
          {lates.map((req) => {
            const meta = requestStatusMeta(req.status);
            return (
              <div key={req.id} className="rounded-2xl bg-white/60 p-3.5 ring-1 ring-white/80">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-indigo-950">
                    {formatJalaliDate(req.work_date)} · خروج {formatTime(req.check_out_at)}
                  </p>
                  <Chip className={meta.chip}>{meta.label}</Chip>
                </div>
                <p className="mt-1.5 text-xs leading-6 text-indigo-900/70">{req.description}</p>
                <p className="mt-1 text-[11px] text-indigo-900/55">
                  {req.branch_name} · فاصله {toFa(Math.round(req.distance_m))} متر
                </p>
                {req.decision_note && (
                  <p className="mt-1 text-[11px] text-indigo-900/55">یادداشت مدیر: {req.decision_note}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

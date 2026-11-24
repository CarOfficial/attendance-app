# قرارداد API سامانه حضوریار — نسخه ۲

همه مسیرها زیر `/api/v1` هستند. احراز هویت با `Authorization: Bearer <token>`.

## ۱. احراز هویت

| متد | مسیر | بدنه/پارامتر | خروجی |
|---|---|---|---|
| POST | `/auth/login` | `{username, password}` | `{access_token, token_type, must_change_password}` |
| GET | `/auth/me` | — | `{id, username, full_name, role, is_active, must_change_password, branch_ids}` |
| POST | `/auth/change-password` | `{current_password, new_password}` | همان خروجی login (توکن تازه) |

خطاها: `401` نامعتبر، `429` قفل ۱۵ دقیقه‌ای، `403` با هدر `X-Password-Change-Required: 1` یعنی رمز باید عوض شود.

## ۲. کارمند — حضور و غیاب

| متد | مسیر | بدنه/پارامتر | خروجی |
|---|---|---|---|
| GET | `/attendance/today` | — | `{status: "not_checked_in"\|"checked_in"\|"checked_out", record: AttendanceOut\|null}` |
| POST | `/attendance/check-in` | `{latitude, longitude, accuracy_m}` | `AttendanceOut` (201) |
| POST | `/attendance/check-out` | `{latitude, longitude, accuracy_m, work_description}` | `AttendanceOut` |
| GET | `/attendance/history?from_date&to_date` | — | `AttendanceOut[]` |
| GET | `/attendance/week?start=YYYY-MM-DD` | `start` اختیاری؛ پیش‌فرض شنبه همین هفته | `WeekOut` |
| POST | `/attendance/late-checkout` | `{work_date, check_out_time:"HH:MM", latitude, longitude, accuracy_m, description}` | `LateCheckoutOut` (201) |
| GET | `/attendance/late-checkouts` | — | `LateCheckoutOut[]` (درخواست‌های خودم) |

### AttendanceOut
```
{id, user_id, user_full_name, work_date, branch_id, branch_name,
 check_in_at(ISO-UTC), check_out_at(ISO-UTC)|null, edited_by_admin,
 work_description|null, check_out_source: "employee"|"late"|"admin"|null,
 approval_status: "none"|"approved"|"rejected", approval_note|null,
 hours_worked: float|null}
```

### WeekOut
```
{start, end, days: DayStateOut[], schedule: ScheduleOut}
```
### DayStateOut
```
{date:"YYYY-MM-DD", is_work_day:bool, status, check_in_at|null, check_out_at|null,
 hours_worked|null, branch_name|null, work_description|null,
 approval_status:"none"|"approved"|"rejected", approval_note|null,
 late_request_status:"pending"|"approved"|"rejected"|"expired"|null,
 pending_leave:bool, is_late:bool, left_early:bool}
```
**statusها (فارسی):**
| مقدار | برچسب فارسی | مفهوم |
|---|---|---|
| `present` | حاضر | ورود+خروج ثبت شده |
| `working` | در حال کار | الان داخل شرکت است (ورود زده، خروج نه) |
| `absent` | غایب | روز کاری بدون ثبت ورود |
| `incomplete` | غایب (خروج ثبت نشده) | ورود دارد، خروج ندارد و درخواستی هم نیست |
| `rejected` | رد شده توسط مدیر | غایب حساب می‌شود |
| `leave` | مرخصی | مرخصی تاییدشده |
| `pending_checkout` | در انتظار تایید خروج | درخواست خروج فراموش‌شده در انتظار مدیر |
| `non_working` | غیرکاری | خارج از روزهای کاری |
| `future` | پیش رو | روز آینده |

`pending_leave=true` یعنی مرخصی در انتظار تایید برای این روز دارد (ولی فعلاً غایب محسوب می‌شود).

### ScheduleOut
```
{work_days: int[] (0=دوشنبه … 6=یکشنبه؛ 5=شنبه)، start_time:"HH:MM", end_time:"HH:MM",
 late_grace_minutes:int, updated_at}
```

### LateCheckoutOut
```
{id, user_id, user_full_name, work_date, record_id, requested_at, check_out_at,
 description, status, branch_name, distance_m, decided_at, decision_note,
 submission_deadline, decision_deadline}
```

## ۳. کارمند — مرخصی

| متد | مسیر | بدنه | خروجی |
|---|---|---|---|
| POST | `/leaves` | `{start_date, end_date, reason}` | `LeaveOut` (201) |
| GET | `/leaves/mine` | — | `LeaveOut[]` |

### LeaveOut
```
{id, user_id, user_full_name, start_date, end_date, reason,
 status:"pending"|"approved"|"rejected", created_at, decided_at|null, decision_note|null}
```

## ۴. مدیر

### داشبورد
`GET /admin/dashboard` →
```
{date, active_employees, present_today, absent_today, leave_today, rejected_today,
 open_check_ins, pending_leaves, pending_late_checkouts}
```

### کارمندان (بدون تغییر)
- `GET /admin/employees?include_inactive` → `UserOut[]` (`{id, username, full_name, role, is_active, must_change_password, branch_ids}`)
- `POST /admin/employees` `{username, full_name, password, branch_ids}` → 201
- `PATCH /admin/employees/{id}` `{full_name?, is_active?, branch_ids?}`
- `POST /admin/employees/{id}/reset-password` `{new_password}` → 204

### شعب/موقعیت (بدون تغییر)
- `GET/POST /admin/branches`، `PATCH /admin/branches/{id}`
- فیلدها: `{name, address?, latitude, longitude, radius_m(20..1000), is_active}`

### حضور و غیاب
- `GET /admin/attendance?from_date&to_date&user_id&branch_id&limit&offset` → `AttendanceOut[]`
- `PATCH /admin/attendance/{id}` `{branch_id?, check_in_at?, check_out_at?}` (ISO با timezone)
- `PATCH /admin/attendance/{id}/decision` `{decision:"approve"|"reject", note?}` → `{id, approval_status, approval_note}`
  - فقط روی رکوردهایی که خروج دارند مجاز است (وگرنه 422)

### مرخصی‌ها
- `GET /admin/leaves?status&user_id&limit` → `LeaveOut[]`
- `PATCH /admin/leaves/{id}` `{decision, note?}` → `LeaveOut`

### خروج جابه‌جا (فراموشی خروج)
- `GET /admin/late-checkouts?status&user_id&limit` → `LateCheckoutOut[]`
- `PATCH /admin/late-checkouts/{id}` `{decision, note?}` → `LateCheckoutOut`
  - approve: خروج با ساعت ادعاشده روی رکورد ثبت می‌شود و روز «حاضر» می‌شود
  - reject: روز «rejected» یعنی غایب

### برنامه کاری
- `GET /admin/schedule` → `ScheduleOut`
- `PATCH /admin/schedule` `{work_days:[0..6], start_time, end_time, late_grace_minutes}` → `ScheduleOut`

### گزارش هفتگی/جمعی کارمند
- `GET /admin/week?user_id&start` → `WeekOut`
- `GET /admin/summary?user_id&from_date&to_date` →
  `{user_id, user_full_name, from_date, to_date, days: DayStateOut[], totals}`
  - `totals`: `{present, absent, leave, pending_checkout, non_working, future, total_hours, late_count, early_leave_count}`
  - بازه حداکثر ۴۰۰ روز

### خروجی اکسل
- `GET /admin/export/excel?user_id&from_date&to_date` → فایل xlsx (همه کارمندان اگر user_id ندهی)
  - باید با `fetch` + هدر Authorization گرفته شود و به صورت Blob دانلود شود
  - پیش‌فرض بازه: ۳۰ روز اخیر

## ۵. مدیر داخل اپ (PWA/اندروید)
مدیر (`role="admin"`) می‌تواند با همان اپ لاگین کند و بخش مدیریت (داشتبورد، تایید مرخصی، تایید خروج فراموش‌شده، مشاهده حضور و غیاب) را ببیند. مسیرهای بالا همه با توکن مدیر کار می‌کنند.

## ۶. پیام‌های خطای انگلیسی سرور و ترجمه فارسی آنها
برای `apiErrors.ts` و `Messages.kt`:

| detail (سرور) | فارسی |
|---|---|
| `Invalid username or password` | نام کاربری یا رمز عبور اشتباه است |
| `Account temporarily locked. Try again later.` | حساب به دلیل تلاش‌های ناموفق قفل شد. ۱۵ دقیقه دیگر دوباره امتحان کنید |
| `Password change required` | ابتدا رمز عبور خود را تغییر دهید |
| `Current password is incorrect` | رمز عبور فعلی اشتباه است |
| `New password must be different from the current one` | رمز جدید باید با رمز فعلی متفاوت باشد |
| `You are outside the allowed area. Nearest branch: …` | در محدوده مجاز شرکت نیستید (نزدیک‌ترین شعبه: …) |
| `GPS accuracy too low (… m). Move to an open area and try again.` | دقت موقعیت مکانی پایین است؛ به فضای باز بروید و دوباره تلاش کنید |
| `No active branch is assigned to you` | شعبه‌ای برای شما تعریف نشده است |
| `You have already checked in today` | امروز قبلاً ثبت ورود کرده‌اید |
| `No open check-in found` | ثبت ورود بازی وجود ندارد |
| `You must be … to check out (… m away).` | برای ثبت خروج باید داخل شعبه باشید (… متر فاصله) |
| `Check-out for {date} was never recorded. Use the forgotten check-out request to fix it.` | خروج {تاریخ} ثبت نشده؛ از بخش «فراموشی خروج» اقدام کنید |
| `A short description of today's work is required` | شرح کار روزانه الزامی است |
| `A short description of the work is required` | شرح کار الزامی است |
| `You have an approved leave for today` | امروز مرخصی تاییدشده دارید |
| `work_date must be a past day` | فقط می‌توان برای روزهای گذشته درخواست ثبت کرد |
| `The 24-hour window for reporting this check-out has passed` | مهلت ۲۴ ساعته ثبت خروج تمام شده است |
| `That day is not a working day` | آن روز، روز کاری نیست |
| `No check-in found for {date}` | برای آن روز ثبت ورودی وجود ندارد |
| `Check-out is already recorded for that day` | خروج آن روز قبلاً ثبت شده است |
| `A request for that day already exists ({status})` | برای آن روز درخواستی ثبت شده است ({status}) |
| `Check-out time must be after check-in` | ساعت خروج باید بعد از ساعت ورود باشد |
| `Check-out time cannot be in the future` | ساعت خروج نمی‌تواند در آینده باشد |
| `Request is already {status}` | درخواست قبلاً بررسی شده است ({status}) |
| `Leave request is already {status}` | درخواست مرخصی قبلاً بررسی شده است ({status}) |
| `start_date must not be after end_date` | تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد |
| `Leave cannot start more than 3 days in the past` | مرخصی حداکثر برای ۳ روز گذشته قابل ثبت است |
| `Leave range is too long` | بازه مرخصی بیش از حد طولانی است |
| `You already have a pending or approved leave for these dates` | برای این تاریخ‌ها مرخصی در انتظار یا تاییدشده دارید |
| `Reason is too short` | دلیل مرخصی را کامل بنویسید |
| `This day has no check-out; use the forgotten check-out request instead` | این روز خروج ندارد؛ ابتدا خروج فراموش‌شده را ثبت کنید |
| `from_date must be before to_date` | تاریخ شروع باید قبل از تاریخ پایان باشد |
| `Date range too large (max 400 days)` | بازه تاریخ بیش از حد طولانی است (حداکثر ۴۰۰ روز) |
| `Employee not found` | کارمند پیدا نشد |
| `Leave request not found` | درخواست مرخصی پیدا نشد |
| `Request not found` | درخواست پیدا نشد |
| `Attendance record not found` | رکورد حضور و غیاب پیدا نشد |
| `Admin only` | فقط مدیر |
| `Invalid or expired token` | نشست شما منقضی شده؛ دوباره وارد شوید |

## ۷. برندینگ
- **نام سامانه: «حضوریار»** (HozoorYar) — شعار: «همراه هوشمند حضور و غیاب»
- تم: **بنفش سلطنتی** (`#4C1D95`, `#6B21A8`, `#7E22CE`, `#A855F7`) + **طلایی** (`#FBBF24`, `#D4A017`)، پس‌زمینه `#F5F1FF`، فونت وزیرمتن
- لوگو: `brand/logo.png` (موجود در ریشه پروژه) — در پنل ادمین به `admin/public/logo.png` و در PWA به `pwa/public/logo.png` کپی شود
- تقویم تاریخ‌ها شمسی (jalaali-js در فرانت‌ها موجود است)

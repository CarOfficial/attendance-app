package com.attendance.app.util

import com.google.gson.JsonParser
import retrofit2.HttpException
import java.io.IOException

/** Persian text for every error the user can see. */
fun Throwable.toUserMessage(): String = when (this) {
    is com.attendance.app.location.LocationException -> message ?: "خطای موقعیت مکانی"
    is IOException -> "اتصال به سرور برقرار نشد. اینترنت را بررسی کنید."
    is HttpException -> {
        val detail = runCatching {
            JsonParser.parseString(response()?.errorBody()?.string().orEmpty())
                .asJsonObject.get("detail")?.asString
        }.getOrNull()
        when (code()) {
            401 -> "نشست شما منقضی شده است. دوباره وارد شوید."
            429 -> "حساب موقتاً قفل شده است. کمی بعد تلاش کنید."
            else -> detail?.let { toPersian(it) } ?: "خطای سرور (${code()})"
        }
    }
    else -> message ?: "خطای نامشخص"
}

/** Maps the API's English details to Persian (contract §6), keeping dynamic values. */
fun toPersian(detail: String): String {
    // --- details with embedded values (regexes must run before the generic list) ---
    Regex("You are outside the allowed area\\. Nearest branch: (.+) \\(~(\\d+) m\\)\\.?").find(detail)?.let {
        return "در محدوده مجاز شرکت نیستید (نزدیک‌ترین شعبه: ${it.groupValues[1]}، حدود ${DateFmt.fa(it.groupValues[2])} متر)"
    }
    Regex("You must be at (.+) to check out \\(~(\\d+) m away\\)\\.?").find(detail)?.let {
        return "برای ثبت خروج باید داخل شعبه باشید (${it.groupValues[1]}، حدود ${DateFmt.fa(it.groupValues[2])} متر فاصله)"
    }
    Regex("Check-out for (.+) was never recorded\\. Use the forgotten check-out request to fix it\\.").find(detail)?.let {
        return "خروج ${it.groupValues[1]} ثبت نشده؛ از بخش «فراموشی خروج» اقدام کنید"
    }
    Regex("No check-in found for (.+)").find(detail)?.let {
        return "برای ${it.groupValues[1]} ثبت ورودی وجود ندارد"
    }
    Regex("A request for that day already exists \\((.+)\\)").find(detail)?.let {
        return "برای آن روز درخواستی ثبت شده است (${it.groupValues[1]})"
    }
    Regex("GPS accuracy too low \\((.+) m\\)").find(detail)?.let {
        return "دقت موقعیت مکانی پایین است (${it.groupValues[1]} متر)؛ به فضای باز بروید و دوباره تلاش کنید"
    }

    return when {
        detail.startsWith("Invalid username") -> "نام کاربری یا رمز عبور اشتباه است"
        detail.startsWith("Account temporarily locked") ->
            "حساب به دلیل تلاش‌های ناموفق قفل شد. ۱۵ دقیقه دیگر دوباره امتحان کنید"
        detail.startsWith("Password change required") -> "ابتدا رمز عبور خود را تغییر دهید"
        detail.startsWith("Current password is incorrect") -> "رمز عبور فعلی اشتباه است"
        detail.startsWith("New password must be different") -> "رمز جدید باید با رمز فعلی متفاوت باشد"
        detail.startsWith("GPS accuracy too low") ->
            "دقت موقعیت مکانی پایین است؛ به فضای باز بروید و دوباره تلاش کنید"
        detail.startsWith("No active branch") -> "شعبه‌ای برای شما تعریف نشده است"
        detail.contains("already checked in today") -> "امروز قبلاً ثبت ورود کرده‌اید"
        detail.startsWith("No open check-in") -> "ثبت ورود بازی وجود ندارد"
        detail.startsWith("There is an open check-in") ->
            "ثبت ورود روز قبل بدون خروج باقی مانده است. با مدیر تماس بگیرید"
        detail.startsWith("A short description of today's work") -> "شرح کار روزانه الزامی است"
        detail.startsWith("A short description of the work") -> "شرح کار الزامی است"
        detail.startsWith("You have an approved leave") -> "امروز مرخصی تاییدشده دارید"
        detail.startsWith("work_date must be a past day") -> "فقط می‌توان برای روزهای گذشته درخواست ثبت کرد"
        detail.startsWith("The 24-hour window") -> "مهلت ۲۴ ساعته ثبت خروج تمام شده است"
        detail.startsWith("That day is not a working day") -> "آن روز، روز کاری نیست"
        detail.startsWith("Check-out for ") && detail.contains("was never recorded") ->
            "خروج ثبت نشده؛ از بخش «فراموشی خروج» اقدام کنید"
        detail.startsWith("No check-in found") -> "برای آن روز ثبت ورودی وجود ندارد"
        detail.startsWith("Check-out is already recorded") -> "خروج آن روز قبلاً ثبت شده است"
        detail.startsWith("A request for that day already exists") -> "برای آن روز درخواستی ثبت شده است"
        detail.startsWith("Check-out time must be after check-in") -> "ساعت خروج باید بعد از ساعت ورود باشد"
        detail.startsWith("Check-out time cannot be in the future") -> "ساعت خروج نمی‌تواند در آینده باشد"
        detail.startsWith("Leave request is already") ->
            "درخواست مرخصی قبلاً بررسی شده است (${detail.removePrefix("Leave request is already").trim().trim('(', ')')})"
        detail.startsWith("Request is already") ->
            "درخواست قبلاً بررسی شده است (${detail.removePrefix("Request is already").trim().trim('(', ')')})"
        detail.startsWith("start_date must not be after end_date") ->
            "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد"
        detail.startsWith("Leave cannot start more than 3 days") ->
            "مرخصی حداکثر برای ۳ روز گذشته قابل ثبت است"
        detail.startsWith("Leave range is too long") -> "بازه مرخصی بیش از حد طولانی است"
        detail.startsWith("You already have a pending or approved leave") ->
            "برای این تاریخ‌ها مرخصی در انتظار یا تاییدشده دارید"
        detail.startsWith("Reason is too short") -> "دلیل مرخصی را کامل بنویسید"
        detail.startsWith("This day has no check-out") ->
            "این روز خروج ندارد؛ ابتدا خروج فراموش‌شده را ثبت کنید"
        detail.startsWith("from_date must be before to_date") -> "تاریخ شروع باید قبل از تاریخ پایان باشد"
        detail.startsWith("Date range too large") -> "بازه تاریخ بیش از حد طولانی است (حداکثر ۴۰۰ روز)"
        detail.startsWith("Employee not found") -> "کارمند پیدا نشد"
        detail.startsWith("Leave request not found") -> "درخواست مرخصی پیدا نشد"
        detail.startsWith("Attendance record not found") -> "رکورد حضور و غیاب پیدا نشد"
        detail.startsWith("Request not found") -> "درخواست پیدا نشد"
        detail.startsWith("Admin only") -> "فقط مدیر"
        detail.startsWith("Invalid or expired token") -> "نشست شما منقضی شده؛ دوباره وارد شوید"
        else -> detail
    }
}

package com.attendance.app.util

import java.time.DayOfWeek
import java.time.Instant
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId

/**
 * Times and dates shown to employees: Tehran time, Persian digits, Jalali calendar.
 *
 * Android's ICU does not ship a Persian calendar, so the Jalali conversion is done here with the
 * standard jalaali algorithm (accurate for the supported Jalali years 1178–1633).
 */
object DateFmt {
    private val tehran: ZoneId = ZoneId.of("Asia/Tehran")
    private val jalaliMonths = arrayOf(
        "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
        "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
    )

    /** ISO datetime from the API (UTC offset included) -> "HH:mm" in Tehran. */
    fun time(iso: String?): String {
        if (iso == null) return "—"
        val t = OffsetDateTime.parse(iso).atZoneSameInstant(tehran)
        return fa("%02d:%02d".format(t.hour, t.minute))
    }

    /** "yyyy-MM-dd" (Gregorian) -> "۱۴۰۵/۰۸/۱۱". */
    fun jalaliDate(isoDate: String): String = jalaliFromLocalDate(LocalDate.parse(isoDate))

    fun todayJalali(): String = jalaliFromLocalDate(LocalDate.now(tehran))

    fun todayIso(): String = LocalDate.now(tehran).toString()

    fun hour(): Int = java.time.LocalTime.now(tehran).hour

    private fun jalaliFromLocalDate(date: LocalDate): String {
        val (y, m, d) = gregorianToJalali(date.year, date.monthValue, date.dayOfMonth)
        return fa("%04d/%02d/%02d".format(y, m, d))
    }

    private fun jalaliFromMillis(millis: Long): String =
        jalaliFromLocalDate(Instant.ofEpochMilli(millis).atZone(tehran).toLocalDate())

    fun monthName(isoDate: String): String {
        val date = LocalDate.parse(isoDate)
        val (_, m, _) = gregorianToJalali(date.year, date.monthValue, date.dayOfMonth)
        return jalaliMonths[m - 1]
    }

    /** Replaces ASCII digits with Persian digits. */
    fun fa(text: String): String = buildString(text.length) {
        for (c in text) append(if (c in '0'..'9') '۰' + (c - '0') else c)
    }

    /** Saturday of the week that contains today (Persian week starts on شنبه). */
    fun currentWeekSaturday(): String {
        val today = LocalDate.now(tehran)
        val sinceSaturday = (today.dayOfWeek.value - DayOfWeek.SATURDAY.value + 7) % 7
        return today.minusDays(sinceSaturday.toLong()).toString()
    }

    /** Shifts a "yyyy-MM-dd" string by a number of days. */
    fun shiftDays(isoDate: String, days: Int): String =
        LocalDate.parse(isoDate).plusDays(days.toLong()).toString()

    /** Yesterday in Tehran, "yyyy-MM-dd". */
    fun yesterdayIso(): String = LocalDate.now(tehran).minusDays(1).toString()

    /** First day of the Jalali month that contains isoDate, as "yyyy-MM-dd". */
    fun jalaliMonthStart(isoDate: String): String {
        val d = LocalDate.parse(isoDate)
        val (jy, jm, _) = gregorianToJalali(d.year, d.monthValue, d.dayOfMonth)
        val (gy, gm, gd) = jalaliToGregorian(jy, jm, 1)
        return "%04d-%02d-%02d".format(gy, gm, gd)
    }

    /** First day of the Jalali month shifted by delta months. */
    fun shiftJalaliMonth(isoDate: String, delta: Int): String {
        val d = LocalDate.parse(jalaliMonthStart(isoDate))
        val (jy, jm, _) = gregorianToJalali(d.year, d.monthValue, d.dayOfMonth)
        val total = jy * 12 + (jm - 1) + delta
        val nj = total / 12
        val nm = total % 12 + 1
        val (gy, gm, gd) = jalaliToGregorian(nj, nm, 1)
        return "%04d-%02d-%02d".format(gy, gm, gd)
    }

    /** Last day of the Jalali month that starts at isoDate. */
    fun jalaliMonthEnd(isoDate: String): String =
        LocalDate.parse(shiftJalaliMonth(isoDate, 1)).minusDays(1).toString()

    /** "مهر ۱۴۰۵" for a date inside that Jalali month. */
    fun monthTitle(isoDate: String): String = monthName(isoDate) + " " + fa(
        gregorianToJalali(
            LocalDate.parse(isoDate).year,
            LocalDate.parse(isoDate).monthValue,
            LocalDate.parse(isoDate).dayOfMonth,
        ).first.toString(),
    )

    /** Persian name of the weekday: شنبه … جمعه. */
    fun dayName(isoDate: String): String = when (LocalDate.parse(isoDate).dayOfWeek) {
        DayOfWeek.SATURDAY -> "شنبه"
        DayOfWeek.SUNDAY -> "یکشنبه"
        DayOfWeek.MONDAY -> "دوشنبه"
        DayOfWeek.TUESDAY -> "سه‌شنبه"
        DayOfWeek.WEDNESDAY -> "چهارشنبه"
        DayOfWeek.THURSDAY -> "پنجشنبه"
        DayOfWeek.FRIDAY -> "جمعه"
    }

    /** Jalali date for a "yyyy-MM-dd" string, or null when it cannot be parsed. */
    fun jalaliAny(iso: String?): String? {
        if (iso.isNullOrBlank()) return null
        return runCatching { jalaliDate(iso.take(10)) }.getOrNull()
    }

    /** Tehran "HH:mm" for an ISO datetime; falls back to the raw text (e.g. "17:00"). */
    fun timeOrRaw(iso: String?): String {
        if (iso.isNullOrBlank()) return "—"
        return runCatching { time(iso) }.getOrNull() ?: fa(iso)
    }

    /** A Jalali text field value ("۱۴۰۵/۰۸/۱۱" or "1405/8/11") -> Gregorian "yyyy-MM-dd", or null. */
    fun jalaliTextToIso(text: String): String? {
        val normalized = toAsciiDigits(text).trim().replace('-', '/').replace('.', '/')
        val parts = normalized.split('/').filter { it.isNotBlank() }
        if (parts.size != 3) return null
        val jy = parts[0].toIntOrNull() ?: return null
        val jm = parts[1].toIntOrNull() ?: return null
        val jd = parts[2].toIntOrNull() ?: return null
        if (jy !in 1200..1600 || jm !in 1..12 || jd !in 1..31) return null
        val (gy, gm, gd) = jalaliToGregorian(jy, jm, jd)
        // Reject impossible days such as 31 اسفند by checking the round trip.
        val (ry, rm, rd) = gregorianToJalali(gy, gm, gd)
        if (ry != jy || rm != jm || rd != jd) return null
        return "%04d-%02d-%02d".format(gy, gm, gd)
    }

    /** Replaces Persian/Arabic-Indic digits with ASCII digits. */
    fun toAsciiDigits(text: String): String = buildString(text.length) {
        for (c in text) {
            append(
                when (c) {
                    in '۰'..'۹' -> '0' + (c - '۰')
                    in '٠'..'٩' -> '0' + (c - '٠')
                    else -> c
                },
            )
        }
    }

    /** "yyyy-MM-dd" or a full ISO datetime -> "۱۴۰۵/۰۸/۱۱" or "۱۴۰۵/۰۸/۱۱ ۱۷:۳۰" in Tehran. */
    fun jalaliDateTime(iso: String?): String {
        if (iso.isNullOrBlank()) return "—"
        val dt = runCatching { OffsetDateTime.parse(iso) }.getOrNull() ?: return jalaliAny(iso) ?: fa(iso)
        val t = dt.atZoneSameInstant(tehran)
        val date = jalaliFromMillis(t.toInstant().toEpochMilli())
        return "$date ${fa("%02d:%02d".format(t.hour, t.minute))}"
    }

    private fun div(a: Int, b: Int): Int = a / b

    /** Gregorian y/m/d -> Jalali y/m/d (jalaali algorithm, month 1..12). */
    fun gregorianToJalali(gy0: Int, gm: Int, gd: Int): Triple<Int, Int, Int> {
        val gDaysInMonth = intArrayOf(0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
        var jy = if (gy0 <= 1600) 0 else 979
        var gy = gy0 - if (gy0 <= 1600) 621 else 1600
        val gy2 = if (gm > 2) gy + 1 else gy
        var days = 365 * gy + div(gy2 + 3, 4) - div(gy2 + 99, 100) + div(gy2 + 399, 400) -
            80 + gd + gDaysInMonth[gm - 1]
        jy += 33 * div(days, 12053)
        days %= 12053
        jy += 4 * div(days, 1461)
        days %= 1461
        if (days > 365) {
            jy += div(days - 1, 365)
            days = (days - 1) % 365
        }
        val jm = if (days < 186) 1 + div(days, 31) else 7 + div(days - 186, 30)
        val jd = 1 + if (days < 186) days % 31 else (days - 186) % 30
        return Triple(jy, jm, jd)
    }

    /** Jalali y/m/d -> Gregorian y/m/d (jalaali algorithm). */
    fun jalaliToGregorian(jy0: Int, jm: Int, jd: Int): Triple<Int, Int, Int> {
        var gy = if (jy0 <= 979) 621 else 1600
        val jy = jy0 - if (jy0 <= 979) 0 else 979
        var days = 365 * jy + div(jy, 33) * 8 + div(jy % 33 + 3, 4) + 78 + jd +
            if (jm < 7) (jm - 1) * 31 else (jm - 7) * 30 + 186
        gy += 400 * div(days, 146097)
        days %= 146097
        if (days > 36524) {
            days -= 1
            gy += 100 * div(days, 36524)
            days %= 36524
            if (days >= 365) days += 1
        }
        gy += 4 * div(days, 1461)
        days %= 1461
        if (days > 365) {
            gy += div(days - 1, 365)
            days = (days - 1) % 365
        }
        var gd = days + 1
        val leap = (gy % 4 == 0 && gy % 100 != 0) || gy % 400 == 0
        val monthLengths = intArrayOf(
            0, 31, if (leap) 29 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31,
        )
        var gm = 0
        while (gm < 12 && gd > monthLengths[gm + 1]) {
            gd -= monthLengths[gm + 1]
            gm += 1
        }
        return Triple(gy, gm + 1, gd)
    }
}

package com.attendance.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.attendance.app.data.DayStateOut
import com.attendance.app.data.SummaryOut
import com.attendance.app.ui.components.GlassCard
import com.attendance.app.ui.components.NoticeBanner
import com.attendance.app.ui.components.StatusPill
import com.attendance.app.ui.components.StatusTone
import com.attendance.app.ui.theme.Palette
import com.attendance.app.util.DateFmt
import kotlin.math.roundToInt

/** گزارش ماهانه حضور، ساعت کاری، تاخیر و اضافه‌کاری کارمند + ثبت علت غیاب. */
@Composable
fun ReportsScreen(
    summary: SummaryOut?,
    busy: Boolean,
    onLoad: (String, String) -> Unit,
    onSubmitAbsenceReason: (String, String) -> Unit,
    modifier: Modifier = Modifier,
) {
    var monthStart by rememberSaveable { mutableStateOf(DateFmt.jalaliMonthStart(DateFmt.todayIso())) }

    LaunchedEffect(monthStart) {
        onLoad(monthStart, DateFmt.jalaliMonthEnd(monthStart))
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("گزارش ماهانه من", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                Text(
                    "ساعت کاری، تاخیر، اضافه‌کاری و علت غیاب",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.TextMuted,
                )
            }
        }

        item {
            GlassCard {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    TextButton(onClick = { monthStart = DateFmt.shiftJalaliMonth(monthStart, -1) }) {
                        Text("‹ ماه قبل", color = Palette.Purple600)
                    }
                    Text(
                        DateFmt.monthTitle(monthStart),
                        style = MaterialTheme.typography.titleMedium,
                        color = Palette.Indigo950,
                    )
                    TextButton(onClick = { monthStart = DateFmt.shiftJalaliMonth(monthStart, 1) }) {
                        Text("ماه بعد ›", color = Palette.Purple600)
                    }
                }
                TextButton(
                    onClick = { monthStart = DateFmt.jalaliMonthStart(DateFmt.todayIso()) },
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                ) {
                    Text("بازگشت به ماه جاری", color = Palette.Purple800)
                }
            }
        }

        val totals = summary?.totals
        if (totals != null) {
            item {
                GlassCard {
                    Text("خلاصه ماه", style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                    StatRow("روزهای حاضر", DateFmt.fa(totals.present.toString()))
                    StatRow("روزهای غایب", DateFmt.fa(totals.absent.toString()))
                    StatRow("مرخصی", DateFmt.fa(totals.leave.toString()))
                    StatRow("مجموع ساعت کاری", hoursLabel(totals.total_hours))
                    StatRow("مجموع تاخیر", minutesLabel(totals.late_minutes))
                    StatRow("مجموع اضافه‌کاری", minutesLabel(totals.overtime_minutes))
                    StatRow("تعداد دفعات تاخیر", DateFmt.fa(totals.late_count.toString()))
                }
            }
        }

        if (summary == null) {
            item {
                GlassCard {
                    Text("در حال دریافت گزارش…", style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
                }
            }
            return@LazyColumn
        }

        if (busy) {
            item { NoticeBanner("در حال ذخیره…", false) }
        }

        items(summary.days, key = { it.date }) { day ->
            DayCard(day = day, busy = busy, onSubmitAbsenceReason = onSubmitAbsenceReason)
        }

        item { Text("", style = MaterialTheme.typography.labelSmall, color = Color.Transparent) }
    }
}

@Composable
private fun StatRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
        Text(value, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
    }
}

@Composable
private fun DayCard(
    day: DayStateOut,
    busy: Boolean,
    onSubmitAbsenceReason: (String, String) -> Unit,
) {
    GlassCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(
                    "${DateFmt.jalaliDate(day.date)} · ${DateFmt.dayName(day.date)}",
                    style = MaterialTheme.typography.titleMedium,
                    color = Palette.Indigo950,
                )
                if (!day.is_work_day) {
                    Text("روز غیرکاری", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                }
            }
            StatusPill(dayStatusLabel(day.status), dayStatusTone(day.status))
        }

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
            MiniStat("ورود", DateFmt.time(day.check_in_at), Modifier.weight(1f))
            MiniStat("خروج", DateFmt.time(day.check_out_at), Modifier.weight(1f))
            MiniStat("ساعت کاری", hoursLabel(day.hours_worked), Modifier.weight(1f))
        }

        if (day.hourly_leave_hours > 0) {
            Text(
                "مرخصی ساعتی: ${hoursLabel(day.hourly_leave_hours)}",
                style = MaterialTheme.typography.labelSmall,
                color = Palette.Gold600,
            )
        }

        if (day.late_minutes > 0 || day.overtime_minutes > 0) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                if (day.late_minutes > 0) {
                    StatusPill("تاخیر ${minutesLabel(day.late_minutes)}", StatusTone.Bad)
                }
                if (day.overtime_minutes > 0) {
                    StatusPill("اضافه‌کاری ${minutesLabel(day.overtime_minutes)}", StatusTone.Working)
                }
            }
        }

        day.work_description?.takeIf { it.isNotBlank() }?.let {
            Text(it, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
        }

        if (isAbsentLike(day.status)) {
            if (day.absence_reason != null) {
                Text(
                    "علت غیاب: ${day.absence_reason}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.Rose600,
                )
            } else {
                AbsenceReasonEditor(date = day.date, busy = busy, onSubmit = onSubmitAbsenceReason)
            }
        }
    }
}

@Composable
private fun MiniStat(label: String, value: String, modifier: Modifier = Modifier) {
    Column(modifier = modifier, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
        Text(value, style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
    }
}

@Composable
private fun AbsenceReasonEditor(
    date: String,
    busy: Boolean,
    onSubmit: (String, String) -> Unit,
) {
    var reason by rememberSaveable(date) { mutableStateOf("") }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            "علت غیاب این روز را بنویسید تا مدیر ببیند.",
            style = MaterialTheme.typography.labelSmall,
            color = Palette.TextMuted,
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            OutlinedTextField(
                value = reason,
                onValueChange = { reason = it },
                singleLine = true,
                label = { Text("علت غیاب") },
                modifier = Modifier.weight(1f),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = Palette.Purple500,
                    unfocusedBorderColor = Palette.Purple200,
                    focusedContainerColor = Color.White,
                    unfocusedContainerColor = Palette.Purple50.copy(alpha = 0.7f),
                    focusedLabelColor = Palette.Purple600,
                    cursorColor = Palette.Purple600,
                ),
            )
            TextButton(
                enabled = !busy && reason.trim().length >= 3,
                onClick = { onSubmit(date, reason.trim()) },
            ) {
                Text("ثبت", color = Palette.Purple700)
            }
        }
    }
}

private fun isAbsentLike(status: String): Boolean =
    status == "absent" || status == "incomplete" || status == "rejected"

private fun dayStatusLabel(status: String): String = when (status) {
    "present" -> "حاضر"
    "working" -> "در حال کار"
    "absent" -> "غایب"
    "incomplete" -> "خروج ثبت نشده"
    "rejected" -> "رد شده"
    "leave" -> "مرخصی"
    "pending_checkout" -> "در انتظار خروج"
    "non_working" -> "غیرکاری"
    "future" -> "پیش رو"
    else -> status
}

private fun dayStatusTone(status: String): StatusTone = when (status) {
    "present" -> StatusTone.Working
    "working" -> StatusTone.Working
    "absent", "incomplete", "rejected" -> StatusTone.Bad
    "leave", "pending_checkout" -> StatusTone.Waiting
    else -> StatusTone.Neutral
}

/** 9.5 -> «۹:۳۰» */
private fun hoursLabel(hours: Double?): String {
    if (hours == null) return "—"
    val total = (hours * 60).roundToInt()
    return DateFmt.fa(String.format("%d:%02d", total / 60, total % 60))
}

/** 130 -> «۲:۱۰ ساعت» */
private fun minutesLabel(minutes: Int): String {
    if (minutes <= 0) return "—"
    return DateFmt.fa(String.format("%d:%02d", minutes / 60, minutes % 60)) + " ساعت"
}

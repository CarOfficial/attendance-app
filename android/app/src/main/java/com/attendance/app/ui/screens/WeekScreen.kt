package com.attendance.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.unit.dp
import com.attendance.app.data.DayStateOut
import com.attendance.app.data.WeekOut
import com.attendance.app.ui.components.GlassCard
import com.attendance.app.ui.components.StatusPill
import com.attendance.app.ui.components.StatusTone
import com.attendance.app.ui.theme.Palette
import com.attendance.app.util.DateFmt

/** هفته کاری: هر روز با وضعیت حاضر/غایب/مرخصی و ساعت‌های ورود و خروج. */
@Composable
fun WeekScreen(
    week: WeekOut?,
    onLoad: (String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    var start by rememberSaveable { mutableStateOf<String?>(null) }
    LaunchedEffect(start) { onLoad(start) }

    val days = week?.days.orEmpty()
    val present = days.count { it.status == "present" || it.status == "working" }
    val leave = days.count { it.status == "leave" }
    val absent = days.count {
        it.is_work_day && (it.status == "absent" || it.status == "incomplete" || it.status == "rejected")
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("هفته کاری", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                Text(
                    if (week != null) "${DateFmt.jalaliDate(week.start)} تا ${DateFmt.jalaliDate(week.end)}" else "در حال بارگذاری…",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.TextMuted,
                )
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(onClick = { week?.let { start = DateFmt.shiftDays(it.start, -7) } }) {
                    Text("هفته قبل", color = Palette.Purple600)
                }
                TextButton(onClick = { start = null }) {
                    Text("این هفته", color = Palette.Purple700)
                }
                TextButton(onClick = { week?.let { start = DateFmt.shiftDays(it.start, 7) } }) {
                    Text("هفته بعد", color = Palette.Purple600)
                }
            }
        }

        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                WeekStat("حاضر", present, Palette.Emerald600, Modifier.weight(1f))
                WeekStat("غایب", absent, Palette.Rose600, Modifier.weight(1f))
                WeekStat("مرخصی", leave, Palette.Purple700, Modifier.weight(1f))
            }
        }

        week?.let { w ->
            item {
                GlassCard {
                    Text("ساعت کاری رسمی", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                    Text(
                        "${DateFmt.fa(w.schedule.start_time)} تا ${DateFmt.fa(w.schedule.end_time)}",
                        style = MaterialTheme.typography.titleMedium,
                        color = Palette.Indigo950,
                    )
                    Text(
                        "روزهای کاری: " + w.schedule.work_days.map { dayShort(it) }.joinToString("، "),
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.TextMuted,
                    )
                }
            }
            items(w.days, key = { it.date }) { day -> DayCard(day) }
        }
    }
}

@Composable
private fun WeekStat(label: String, value: Int, color: androidx.compose.ui.graphics.Color, modifier: Modifier) {
    GlassCard(modifier = modifier) {
        Text(DateFmt.fa(value.toString()), style = MaterialTheme.typography.titleLarge, color = color)
        Text(label, style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
    }
}

@Composable
private fun DayCard(day: DayStateOut) {
    GlassCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    "${DateFmt.dayName(day.date)}  ${DateFmt.jalaliDate(day.date)}",
                    style = MaterialTheme.typography.titleMedium,
                    color = Palette.Indigo950,
                )
                val times = when {
                    day.check_in_at == null && day.check_out_at == null ->
                        if (day.is_work_day) "بدون ثبت" else "روز غیرکاری"
                    else ->
                        "ورود ${DateFmt.time(day.check_in_at)}  ·  خروج ${DateFmt.time(day.check_out_at)}"
                }
                Text(times, style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                day.hours_worked?.let {
                    Text(DateFmt.fa("%.1f".format(it)) + " ساعت کارکرد", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                }
            }
            StatusPill(text = statusLabel(day.status), tone = statusTone(day.status))
        }

        if (day.is_late || day.left_early || day.pending_leave) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                if (day.is_late) StatusPill("تاخیر", StatusTone.Waiting)
                if (day.left_early) StatusPill("خروج زودتر", StatusTone.Waiting)
                if (day.pending_leave) StatusPill("مرخصی در انتظار", StatusTone.Neutral)
            }
        }

        day.work_description?.let {
            Text(it, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
        }
        day.approval_note?.let {
            Text("یادداشت مدیر: $it", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
        }
    }
}

private fun statusLabel(status: String): String = when (status) {
    "present" -> "حاضر"
    "working" -> "در حال کار"
    "absent" -> "غایب"
    "incomplete" -> "غایب (بدون خروج)"
    "rejected" -> "رد شده"
    "leave" -> "مرخصی"
    "pending_checkout" -> "در انتظار تایید خروج"
    "non_working" -> "غیرکاری"
    "future" -> "پیش رو"
    else -> status
}

private fun statusTone(status: String): StatusTone = when (status) {
    "present" -> StatusTone.Working
    "working" -> StatusTone.Working
    "leave" -> StatusTone.Done
    "non_working", "future" -> StatusTone.Neutral
    "absent", "incomplete", "rejected" -> StatusTone.Bad
    "pending_checkout" -> StatusTone.Waiting
    else -> StatusTone.Neutral
}

private fun dayShort(day: Int): String = when (day) {
    0 -> "دوشنبه"
    1 -> "سه‌شنبه"
    2 -> "چهارشنبه"
    3 -> "پنجشنبه"
    4 -> "جمعه"
    5 -> "شنبه"
    6 -> "یکشنبه"
    else -> day.toString()
}


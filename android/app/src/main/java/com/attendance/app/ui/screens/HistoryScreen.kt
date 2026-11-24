package com.attendance.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.attendance.app.data.AttendanceRecord
import com.attendance.app.ui.components.GlassCard
import com.attendance.app.ui.components.StatusPill
import com.attendance.app.ui.components.StatusTone
import com.attendance.app.ui.components.TimeTile
import com.attendance.app.ui.theme.Palette
import com.attendance.app.util.DateFmt
import java.time.Duration
import java.time.OffsetDateTime

@Composable
fun HistoryScreen(
    records: List<AttendanceRecord>,
    busy: Boolean,
    onRefresh: () -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text("سوابق حضور", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                    Text("۳۰ روز اخیر", style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
                }
                TextButton(onClick = onRefresh, enabled = !busy) {
                    Text(if (busy) "…" else "به‌روزرسانی", color = Palette.Purple600)
                }
            }
        }
        if (records.isEmpty()) {
            item {
                GlassCard {
                    Text(
                        "هنوز سابقه‌ای ثبت نشده است.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Palette.TextMuted,
                    )
                }
            }
        }
        items(records, key = { it.id }) { record ->
            HistoryItem(record)
        }
    }
}

@Composable
private fun HistoryItem(r: AttendanceRecord) {
    GlassCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text(DateFmt.jalaliDate(r.work_date), style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                Text(r.branch_name, style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
            }
            StatusPill(
                text = workedText(r.check_in_at, r.check_out_at),
                tone = if (r.check_out_at == null) StatusTone.Working else StatusTone.Done,
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            TimeTile("ورود", DateFmt.time(r.check_in_at), Modifier.weight(1f))
            TimeTile("خروج", DateFmt.time(r.check_out_at), Modifier.weight(1f))
        }
        if (r.edited_by_admin) {
            StatusPill(text = "اصلاح‌شده توسط مدیر", tone = StatusTone.Waiting)
        }
    }
}

private fun workedText(checkInAt: String, checkOutAt: String?): String {
    if (checkOutAt == null) return "در حال کار"
    val d = Duration.between(OffsetDateTime.parse(checkInAt), OffsetDateTime.parse(checkOutAt))
    return DateFmt.fa("${d.toHours()} ساعت و ${d.toMinutesPart()} دقیقه")
}

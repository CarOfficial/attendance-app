package com.attendance.app.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import com.attendance.app.data.LateCheckoutOut
import com.attendance.app.data.LeaveOut
import com.attendance.app.ui.components.GlassCard
import com.attendance.app.ui.components.GradientButton
import com.attendance.app.ui.components.NoticeBanner
import com.attendance.app.ui.components.StatusPill
import com.attendance.app.ui.components.StatusTone
import com.attendance.app.ui.theme.Palette
import com.attendance.app.util.DateFmt

/** درخواست مرخصی و ثبت خروج فراموش‌شده (مهلت ۲۴ ساعته، نیازمند تایید مدیر). */
@Composable
fun RequestsScreen(
    leaves: List<LeaveOut>,
    lateCheckouts: List<LateCheckoutOut>,
    fixReady: Boolean,
    busy: Boolean,
    notice: String?,
    noticeIsError: Boolean,
    onSubmitLeave: (String, String, String) -> Unit,
    onFetchLocation: () -> Unit,
    onSubmitLateCheckout: (String, String, String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("درخواست‌ها", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                Text("مرخصی و ثبت خروج فراموش‌شده", style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
            }
        }

        if (notice != null) {
            item { NoticeBanner(notice, noticeIsError) }
        }

        item {
            LeaveForm(busy = busy, onSubmit = onSubmitLeave)
        }

        if (leaves.isNotEmpty()) {
            item {
                Text("درخواست‌های مرخصی من", style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
            }
            items(leaves, key = { "leave-${it.id}" }) { leave ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "${DateFmt.jalaliDate(leave.start_date)} تا ${DateFmt.jalaliDate(leave.end_date)}",
                            style = MaterialTheme.typography.titleMedium,
                            color = Palette.Indigo950,
                        )
                        StatusPill(requestLabel(leave.status), requestTone(leave.status))
                    }
                    Text(leave.reason, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
                    leave.decision_note?.let {
                        Text("یادداشت مدیر: $it", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                    }
                }
            }
        }

        item {
            LateCheckoutForm(
                busy = busy,
                fixReady = fixReady,
                onFetchLocation = onFetchLocation,
                onSubmit = onSubmitLateCheckout,
            )
        }

        if (lateCheckouts.isNotEmpty()) {
            item {
                Text("درخواست‌های خروج", style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
            }
            items(lateCheckouts, key = { "late-${it.id}" }) { req ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            "${DateFmt.jalaliDate(req.work_date)} · خروج ${DateFmt.timeOrRaw(req.check_out_at)}",
                            style = MaterialTheme.typography.titleMedium,
                            color = Palette.Indigo950,
                        )
                        StatusPill(requestLabel(req.status), requestTone(req.status))
                    }
                    req.description?.let {
                        Text(it, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
                    }
                    req.distance_m?.let {
                        Text(
                            "فاصله از دفتر: ${DateFmt.fa(it.toInt().toString())} متر",
                            style = MaterialTheme.typography.labelSmall,
                            color = Palette.TextMuted,
                        )
                    }
                    req.decision_note?.let {
                        Text("یادداشت مدیر: $it", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                    }
                }
            }
        }

        item { Text("", style = MaterialTheme.typography.labelSmall, color = Color.Transparent) }
    }
}

@Composable
private fun LeaveForm(busy: Boolean, onSubmit: (String, String, String) -> Unit) {
    var startText by rememberSaveable { mutableStateOf(DateFmt.todayJalali()) }
    var endText by rememberSaveable { mutableStateOf(DateFmt.todayJalali()) }
    var reason by rememberSaveable { mutableStateOf("") }
    var error by rememberSaveable { mutableStateOf<String?>(null) }

    val startIso = DateFmt.jalaliTextToIso(startText)
    val endIso = DateFmt.jalaliTextToIso(endText)
    val canSubmit = !busy && startIso != null && endIso != null && reason.trim().length >= 3

    GlassCard {
        Text("درخواست مرخصی", style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
        Text(
            "مرخصی فقط پس از تایید مدیر اعمال می‌شود. تاریخ‌ها را شمسی وارد کنید.",
            style = MaterialTheme.typography.labelSmall,
            color = Palette.TextMuted,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            GlassField(startText, { startText = it; error = null }, "از تاریخ", ltr = true, modifier = Modifier.weight(1f))
            GlassField(endText, { endText = it; error = null }, "تا تاریخ", ltr = true, modifier = Modifier.weight(1f))
        }
        if (startIso == null || endIso == null) {
            Text("تاریخ را به شکل ۱۴۰۵/۰۸/۱۱ وارد کنید.", style = MaterialTheme.typography.labelSmall, color = Palette.Rose600)
        }
        MultilineField(reason, { reason = it; error = null }, "دلیل مرخصی", 3)
        error?.let { Text(it, style = MaterialTheme.typography.labelSmall, color = Palette.Rose600) }
        GradientButton(
            text = if (busy) "در حال ارسال…" else "ارسال درخواست مرخصی",
            enabled = canSubmit,
            onClick = {
                if (reason.trim().length < 3) {
                    error = "دلیل مرخصی را کامل بنویسید."
                } else if (startIso != null && endIso != null && endIso < startIso) {
                    error = "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."
                } else if (startIso != null && endIso != null) {
                    error = null
                    onSubmit(startIso, endIso, reason.trim())
                    reason = ""
                }
            },
        )
    }
}

@Composable
private fun LateCheckoutForm(
    busy: Boolean,
    fixReady: Boolean,
    onFetchLocation: () -> Unit,
    onSubmit: (String, String, String) -> Unit,
) {
    var dateText by rememberSaveable { mutableStateOf(DateFmt.jalaliDate(DateFmt.yesterdayIso())) }
    var timeText by rememberSaveable { mutableStateOf("17:00") }
    var description by rememberSaveable { mutableStateOf("") }
    var error by rememberSaveable { mutableStateOf<String?>(null) }

    val iso = DateFmt.jalaliTextToIso(dateText)
    val cleanTime = DateFmt.toAsciiDigits(timeText).trim()
    val timeOk = Regex("^([01]\\d|2[0-3]):[0-5]\\d$").matches(cleanTime)
    val canSubmit = !busy && iso != null && timeOk && description.trim().length >= 3

    GlassCard {
        Text("فراموشی ثبت خروج", style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
        Text(
            "تا ۲۴ ساعت بعد و با حضور در محل کار می‌توانید ساعت خروج روز قبل را ثبت کنید. " +
                "این درخواست باید توسط مدیر تایید شود؛ در غیر این صورت آن روز غایب می‌شود.",
            style = MaterialTheme.typography.labelSmall,
            color = Palette.TextMuted,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            GlassField(dateText, { dateText = it; error = null }, "تاریخ روز گذشته", ltr = true, modifier = Modifier.weight(1f))
            GlassField(timeText, { timeText = it; error = null }, "ساعت خروج", ltr = true, modifier = Modifier.weight(1f))
        }
        if (iso == null) {
            Text("تاریخ را به شکل ۱۴۰۵/۰۸/۱۱ وارد کنید.", style = MaterialTheme.typography.labelSmall, color = Palette.Rose600)
        } else if (!timeOk) {
            Text("ساعت را به شکل ۱۷:۳۰ وارد کنید.", style = MaterialTheme.typography.labelSmall, color = Palette.Rose600)
        }
        MultilineField(description, { description = it; error = null }, "شرح کارهای آن روز", 3)
        error?.let { Text(it, style = MaterialTheme.typography.labelSmall, color = Palette.Rose600) }

        StatusPill(
            text = if (fixReady) "موقعیت مکانی دریافت شد" else "موقعیت مکانی هنوز دریافت نشده",
            tone = if (fixReady) StatusTone.Working else StatusTone.Waiting,
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            GradientButton(
                text = "دریافت موقعیت",
                gold = true,
                enabled = !busy,
                onClick = onFetchLocation,
                modifier = Modifier.weight(1f),
            )
            GradientButton(
                text = if (busy) "…" else "ثبت درخواست",
                enabled = canSubmit,
                onClick = {
                    if (description.trim().length < 3) {
                        error = "شرح کار الزامی است."
                    } else if (iso != null) {
                        error = null
                        onSubmit(iso, cleanTime, description.trim())
                        description = ""
                    }
                },
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun MultilineField(value: String, onValueChange: (String) -> Unit, label: String, lines: Int) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        minLines = lines,
        maxLines = lines + 2,
        modifier = Modifier.fillMaxWidth(),
        textStyle = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Normal),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = Palette.Purple500,
            unfocusedBorderColor = Palette.Purple200,
            focusedContainerColor = Color.White,
            unfocusedContainerColor = Palette.Purple50.copy(alpha = 0.7f),
            focusedLabelColor = Palette.Purple600,
            cursorColor = Palette.Purple600,
        ),
    )
}

internal fun requestLabel(status: String): String = when (status) {
    "pending" -> "در انتظار تایید"
    "approved" -> "تایید شد"
    "rejected" -> "رد شد"
    "expired" -> "منقضی شد"
    else -> status
}

internal fun requestTone(status: String): StatusTone = when (status) {
    "approved" -> StatusTone.Working
    "rejected" -> StatusTone.Bad
    "expired" -> StatusTone.Neutral
    else -> StatusTone.Waiting
}

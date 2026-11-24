package com.attendance.app.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.attendance.app.data.TodayOut
import com.attendance.app.ui.components.CheckOrb
import com.attendance.app.ui.components.NoticeBanner
import com.attendance.app.ui.components.StatusPill
import com.attendance.app.ui.components.StatusTone
import com.attendance.app.ui.components.TimeTile
import com.attendance.app.ui.theme.Palette
import com.attendance.app.util.DateFmt

@Composable
fun HomeScreen(
    userName: String,
    today: TodayOut?,
    busy: Boolean,
    notice: String?,
    noticeIsError: Boolean,
    onAction: (Boolean, String?) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    var pendingAction by remember { mutableStateOf<Pair<Boolean, String?>?>(null) }
    var permissionNotice by remember { mutableStateOf<String?>(null) }
    var showCheckoutDialog by remember { mutableStateOf(false) }
    var workDescription by remember { mutableStateOf("") }

    val launcher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { results ->
        val want = pendingAction
        pendingAction = null
        if (results[Manifest.permission.ACCESS_FINE_LOCATION] == true) {
            if (want != null) onAction(want.first, want.second)
        } else {
            permissionNotice = "برای ثبت حضور باید دسترسی موقعیت مکانی را بدهید."
        }
    }

    fun request(checkIn: Boolean, description: String? = null) {
        permissionNotice = null
        val granted = ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED
        if (granted) {
            onAction(checkIn, description)
        } else {
            pendingAction = checkIn to description
            launcher.launch(
                arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION),
            )
        }
    }

    val status = today?.status
    val record = today?.record
    val isCheckedIn = status == "checked_in"
    val canAct = status == "not_checked_in" || isCheckedIn

    val (pill, tone) = when (status) {
        "checked_in" -> "در حال کار" to StatusTone.Working
        "checked_out" -> "امروز تمام شد" to StatusTone.Done
        "not_checked_in" -> "هنوز ورود نکرده‌اید" to StatusTone.Waiting
        else -> "در حال بارگذاری…" to StatusTone.Waiting
    }

    val shownNotice = permissionNotice ?: notice
    val shownIsError = permissionNotice != null || noticeIsError

    // Check-out needs the daily work description (contract §2): ask first, then call the API.
    if (showCheckoutDialog) {
        val trimmed = workDescription.trim()
        AlertDialog(
            onDismissRequest = { showCheckoutDialog = false },
            title = { Text("ثبت خروج", style = MaterialTheme.typography.titleLarge) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        "شرح کار روزانه الزامی است و برای مدیر ارسال می‌شود.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = Palette.TextMuted,
                    )
                    OutlinedTextField(
                        value = workDescription,
                        onValueChange = { workDescription = it },
                        label = { Text("شرح کار روزانه") },
                        minLines = 3,
                        maxLines = 5,
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = Palette.Purple500,
                            unfocusedBorderColor = Palette.Purple200,
                            focusedLabelColor = Palette.Purple600,
                            cursorColor = Palette.Purple600,
                        ),
                    )
                    if (workDescription.isNotBlank() && trimmed.length < 3) {
                        Text(
                            "حداقل ۳ نویسه بنویسید.",
                            style = MaterialTheme.typography.labelSmall,
                            color = Palette.Rose600,
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(
                    enabled = trimmed.length >= 3,
                    onClick = {
                        showCheckoutDialog = false
                        request(checkIn = false, description = trimmed)
                    },
                ) {
                    Text("ثبت خروج", color = Palette.Purple600)
                }
            },
            dismissButton = {
                TextButton(onClick = { showCheckoutDialog = false }) {
                    Text("انصراف", color = Palette.TextMuted)
                }
            },
        )
    }

    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(18.dp),
    ) {
        Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("سلام، $userName", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
            Text(
                "امروز ${DateFmt.todayJalali()}",
                style = MaterialTheme.typography.bodyMedium,
                color = Palette.TextMuted,
            )
        }

        CheckOrb(
            label = when (status) {
                "checked_in" -> "ثبت خروج"
                "checked_out" -> "پایان"
                else -> "ثبت ورود"
            },
            sublabel = if (status == "checked_out") "تا فردا" else "با GPS در محدوده",
            isCheckOut = isCheckedIn,
            busy = busy,
            enabled = canAct,
            onClick = {
                if (isCheckedIn) {
                    workDescription = ""
                    showCheckoutDialog = true
                } else {
                    request(checkIn = true)
                }
            },
        )

        StatusPill(text = pill, tone = tone)

        if (shownNotice != null) NoticeBanner(shownNotice, shownIsError)

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            TimeTile("ساعت ورود", DateFmt.time(record?.check_in_at), Modifier.weight(1f))
            TimeTile("ساعت خروج", DateFmt.time(record?.check_out_at), Modifier.weight(1f))
        }
        record?.let {
            Text("دفتر: ${it.branch_name}", style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
        }
    }
}

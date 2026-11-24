package com.attendance.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.attendance.app.data.AttendanceRecord
import com.attendance.app.data.BranchOut
import com.attendance.app.data.DashboardOut
import com.attendance.app.data.EmployeeOut
import com.attendance.app.data.LateCheckoutOut
import com.attendance.app.data.LeaveOut
import com.attendance.app.ui.components.GlassCard
import com.attendance.app.ui.components.GradientButton
import com.attendance.app.ui.components.NoticeBanner
import com.attendance.app.ui.components.StatusPill
import com.attendance.app.ui.components.StatusTone
import com.attendance.app.ui.theme.Palette
import com.attendance.app.util.DateFmt

private val SECTIONS = listOf("داشبورد", "مرخصی", "خروج", "حضور", "دفاتر", "کارمندان")

/** پنل مدیریت داخل اپ: داشبورد، درخواست‌ها، حضور، دفاتر و حساب کارمندان. */
@Composable
fun AdminScreen(
    dashboard: DashboardOut?,
    leaves: List<LeaveOut>,
    lateCheckouts: List<LateCheckoutOut>,
    records: List<AttendanceRecord>,
    branches: List<BranchOut>,
    employees: List<EmployeeOut>,
    busy: Boolean,
    notice: String?,
    noticeIsError: Boolean,
    onLoad: (Int) -> Unit,
    onDecideLeave: (Int, String) -> Unit,
    onDecideLateCheckout: (Int, String) -> Unit,
    onDecideAttendance: (Int, String) -> Unit,
    onCreateBranch: (String, String?, Double, Double, Double) -> Unit,
    onDeleteBranch: (Int) -> Unit,
    onCreateEmployee: (String, String, String, List<Int>) -> Unit,
    onSetEmployeeActive: (Int, Boolean) -> Unit,
    onDeleteEmployee: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    var section by rememberSaveable { mutableIntStateOf(0) }
    var showBranchDialog by rememberSaveable { mutableStateOf(false) }
    var showEmployeeDialog by rememberSaveable { mutableStateOf(false) }
    var deleteBranch by remember { mutableStateOf<BranchOut?>(null) }
    var deleteEmployee by remember { mutableStateOf<EmployeeOut?>(null) }

    LaunchedEffect(section) { onLoad(section) }

    if (showBranchDialog) {
        CreateBranchDialog(
            busy = busy,
            onDismiss = { showBranchDialog = false },
            onCreate = { name, address, lat, lng, radius ->
                onCreateBranch(name, address, lat, lng, radius)
                showBranchDialog = false
            },
        )
    }

    if (showEmployeeDialog) {
        CreateEmployeeDialog(
            branches = branches,
            busy = busy,
            onDismiss = { showEmployeeDialog = false },
            onCreate = { name, username, password, branchIds ->
                onCreateEmployee(name, username, password, branchIds)
                showEmployeeDialog = false
            },
        )
    }

    deleteBranch?.let { branch ->
        AlertDialog(
            onDismissRequest = { deleteBranch = null },
            title = { Text("حذف دفتر «${branch.name}»") },
            text = {
                Text(
                    "دفتر حذف می‌شود و سوابق حضور ثبت‌شده در آن هم پاک می‌شوند. این کار برگشت‌پذیر نیست.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        onDeleteBranch(branch.id)
                        deleteBranch = null
                    },
                ) { Text("حذف", color = Palette.Rose600) }
            },
            dismissButton = {
                TextButton(onClick = { deleteBranch = null }) { Text("انصراف", color = Palette.TextMuted) }
            },
        )
    }

    deleteEmployee?.let { emp ->
        AlertDialog(
            onDismissRequest = { deleteEmployee = null },
            title = { Text("حذف حساب ${emp.full_name}") },
            text = {
                Text(
                    "حساب کارمند همراه با سوابق حضور و مرخصی او برای همیشه حذف می‌شود.",
                    style = MaterialTheme.typography.bodyMedium,
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        onDeleteEmployee(emp.id)
                        deleteEmployee = null
                    },
                ) { Text("حذف", color = Palette.Rose600) }
            },
            dismissButton = {
                TextButton(onClick = { deleteEmployee = null }) { Text("انصراف", color = Palette.TextMuted) }
            },
        )
    }

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("پنل مدیریت", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                Text(
                    "مدیریت درخواست‌ها، حضور، دفاتر و کارمندان",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.TextMuted,
                )
            }
        }

        item {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                items(SECTIONS.size) { index ->
                    SectionChip(
                        label = SECTIONS[index],
                        active = section == index,
                        onClick = { section = index },
                    )
                }
            }
        }

        if (notice != null) {
            item { NoticeBanner(notice, noticeIsError) }
        }

        if (section == 0) {
            item { DashboardCard(dashboard) }
        }

        if (section == 1) {
            if (leaves.isEmpty()) {
                item { EmptyCard("درخواست مرخصی در انتظار تایید وجود ندارد.") }
            }
            items(leaves, key = { "admin-leave-${it.id}" }) { leave ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(leave.user_full_name, style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                        StatusPill(requestLabel(leave.status), requestTone(leave.status))
                    }
                    Text(
                        "${DateFmt.jalaliDate(leave.start_date)} تا ${DateFmt.jalaliDate(leave.end_date)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.TextMuted,
                    )
                    Text(leave.reason, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
                    DecisionRow(
                        busy = busy,
                        onApprove = { onDecideLeave(leave.id, "approve") },
                        onReject = { onDecideLeave(leave.id, "reject") },
                    )
                }
            }
        }

        if (section == 2) {
            if (lateCheckouts.isEmpty()) {
                item { EmptyCard("درخواست خروج فراموش‌شده در انتظار تایید وجود ندارد.") }
            }
            items(lateCheckouts, key = { "admin-late-${it.id}" }) { req ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(req.user_full_name, style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                        StatusPill(requestLabel(req.status), requestTone(req.status))
                    }
                    Text(
                        "${DateFmt.jalaliDate(req.work_date)} · خروج ${DateFmt.timeOrRaw(req.check_out_at)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.TextMuted,
                    )
                    req.description?.let {
                        Text(it, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
                    }
                    Text(
                        "با رد کردن، آن روز برای کارمند غایب ثبت می‌شود.",
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.Rose600,
                    )
                    DecisionRow(
                        busy = busy,
                        onApprove = { onDecideLateCheckout(req.id, "approve") },
                        onReject = { onDecideLateCheckout(req.id, "reject") },
                    )
                }
            }
        }

        if (section == 3) {
            if (records.isEmpty()) {
                item { EmptyCard("رکوردی برای نمایش وجود ندارد.") }
            }
            items(records, key = { "admin-rec-${it.id}" }) { rec ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column {
                            Text(rec.user_full_name, style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                            Text(
                                "${DateFmt.jalaliDate(rec.work_date)} · ${rec.branch_name}",
                                style = MaterialTheme.typography.labelSmall,
                                color = Palette.TextMuted,
                            )
                        }
                        StatusPill(approvalLabel(rec.approval_status), approvalTone(rec.approval_status))
                    }
                    Text(
                        "ورود ${DateFmt.time(rec.check_in_at)}  ·  خروج ${DateFmt.time(rec.check_out_at)}",
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.TextMuted,
                    )
                    rec.work_description?.let {
                        Text(it, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
                    }
                    if (rec.check_out_at != null && rec.approval_status == "none") {
                        DecisionRow(
                            busy = busy,
                            onApprove = { onDecideAttendance(rec.id, "approve") },
                            onReject = { onDecideAttendance(rec.id, "reject") },
                        )
                    }
                }
            }
        }

        if (section == 4) {
            item {
                GradientButton(
                    text = "+ افزودن دفتر",
                    enabled = !busy,
                    onClick = { showBranchDialog = true },
                )
            }
            if (branches.isEmpty()) {
                item { EmptyCard("هنوز دفتری ثبت نشده است. با «افزودن دفتر» اولین دفتر را بسازید.") }
            }
            items(branches, key = { "branch-${it.id}" }) { branch ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(branch.name, style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                        StatusPill(
                            text = if (branch.is_active) "فعال" else "غیرفعال",
                            tone = if (branch.is_active) StatusTone.Working else StatusTone.Neutral,
                        )
                    }
                    branch.address?.takeIf { it.isNotBlank() }?.let {
                        Text(it, style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
                    }
                    Text(
                        "${DateFmt.fa(branch.radius_m.toInt().toString())} متر شعاع · " +
                            "${branch.latitude.formatCoord()}, ${branch.longitude.formatCoord()}",
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.TextMuted,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(Color.White)
                                .clickable(enabled = !busy) { deleteBranch = branch }
                                .padding(vertical = 12.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text("حذف دفتر", style = MaterialTheme.typography.labelLarge, color = Palette.Rose600)
                        }
                    }
                }
            }
        }

        if (section == 5) {
            item {
                GradientButton(
                    text = "+ افزودن کارمند",
                    enabled = !busy,
                    onClick = { showEmployeeDialog = true },
                )
            }
            if (employees.isEmpty()) {
                item { EmptyCard("هنوز کارمندی ثبت نشده است.") }
            }
            items(employees, key = { "employee-${it.id}" }) { emp ->
                GlassCard {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column {
                            Text(emp.full_name, style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
                            Text(
                                emp.username,
                                style = MaterialTheme.typography.labelSmall,
                                color = Palette.TextMuted,
                            )
                        }
                        StatusPill(
                            text = if (emp.is_active) "فعال" else "غیرفعال",
                            tone = if (emp.is_active) StatusTone.Working else StatusTone.Bad,
                        )
                    }
                    Text(
                        "دفاتر: " + if (emp.branch_ids.isEmpty()) {
                            "بدون دفتر"
                        } else {
                            emp.branch_ids.mapNotNull { id -> branches.find { it.id == id }?.name }
                                .joinToString("، ")
                                .ifBlank { "${emp.branch_ids.size} دفتر" }
                        },
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.TextMuted,
                    )
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(Color.White)
                                .clickable(enabled = !busy) { onSetEmployeeActive(emp.id, !emp.is_active) }
                                .padding(vertical = 12.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                if (emp.is_active) "غیرفعال کردن" else "فعال کردن",
                                style = MaterialTheme.typography.labelLarge,
                                color = if (emp.is_active) Palette.Gold600 else Palette.Emerald600,
                            )
                        }
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(14.dp))
                                .background(Color.White)
                                .clickable(enabled = !busy) { deleteEmployee = emp }
                                .padding(vertical = 12.dp),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text("حذف", style = MaterialTheme.typography.labelLarge, color = Palette.Rose600)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionChip(label: String, active: Boolean, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(50))
            .background(if (active) Palette.Purple600 else Color.White.copy(alpha = 0.75f))
            .clickable(onClick = onClick)
            .padding(horizontal = 14.dp, vertical = 9.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = if (active) Color.White else Palette.Purple800,
        )
    }
}

@Composable
private fun CreateBranchDialog(
    busy: Boolean,
    onDismiss: () -> Unit,
    onCreate: (String, String?, Double, Double, Double) -> Unit,
) {
    var name by rememberSaveable { mutableStateOf("") }
    var address by rememberSaveable { mutableStateOf("") }
    var lat by rememberSaveable { mutableStateOf("") }
    var lng by rememberSaveable { mutableStateOf("") }
    var radius by rememberSaveable { mutableStateOf("100") }

    fun parse(value: String): Double? = DateFmt.toAsciiDigits(value).trim().toDoubleOrNull()

    val latitude = parse(lat)
    val longitude = parse(lng)
    val radiusM = parse(radius)
    val valid = name.trim().length >= 2 &&
        latitude != null && latitude in -90.0..90.0 &&
        longitude != null && longitude in -180.0..180.0 &&
        radiusM != null && radiusM in 20.0..1000.0

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("دفتر جدید") },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Text(
                    "مختصات دفتر را وارد کنید؛ کارمندان فقط داخل شعاع مجاز می‌توانند ثبت حضور کنند.",
                    style = MaterialTheme.typography.labelSmall,
                    color = Palette.TextMuted,
                )
                GlassField(name, { name = it }, "نام دفتر")
                GlassField(address, { address = it }, "آدرس (اختیاری)")
                GlassField(lat, { lat = it }, "عرض جغرافیایی (مثلاً 35.6892)", ltr = true)
                GlassField(lng, { lng = it }, "طول جغرافیایی (مثلاً 51.3890)", ltr = true)
                GlassField(radius, { radius = it }, "شعاع مجاز به متر (۲۰ تا ۱۰۰۰)", ltr = true)
                if (!valid && (lat.isNotBlank() || lng.isNotBlank())) {
                    Text(
                        "نام و مختصات و شعاع را درست وارد کنید.",
                        style = MaterialTheme.typography.labelSmall,
                        color = Palette.Rose600,
                    )
                }
                GradientButton(
                    text = if (busy) "در حال ذخیره…" else "ذخیره دفتر",
                    enabled = valid && !busy,
                    onClick = {
                        onCreate(
                            name.trim(),
                            address.trim().ifBlank { null },
                            latitude ?: return@GradientButton,
                            longitude ?: return@GradientButton,
                            radiusM ?: 100.0,
                        )
                    },
                )
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("انصراف", color = Palette.TextMuted) }
        },
    )
}

@Composable
private fun CreateEmployeeDialog(
    branches: List<BranchOut>,
    busy: Boolean,
    onDismiss: () -> Unit,
    onCreate: (String, String, String, List<Int>) -> Unit,
) {
    var fullName by rememberSaveable { mutableStateOf("") }
    var username by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var selected by remember { mutableStateOf<List<Int>>(emptyList()) }

    val valid = fullName.trim().length >= 2 && username.trim().length >= 3 && password.length >= 8

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("کارمند جدید") },
        text = {
            Column(
                modifier = Modifier.verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                GlassField(fullName, { fullName = it }, "نام و نام خانوادگی")
                GlassField(username, { username = it }, "نام کاربری (حروف انگلیسی)", ltr = true)
                GlassField(password, { password = it }, "رمز عبور اولیه (حداقل ۸ نویسه)", ltr = true)
                Text(
                    "کارمند در اولین ورود رمز را تغییر می‌دهد.",
                    style = MaterialTheme.typography.labelSmall,
                    color = Palette.TextMuted,
                )
                if (branches.isNotEmpty()) {
                    Text("دفاتر مجاز", style = MaterialTheme.typography.labelLarge, color = Palette.Indigo950)
                    branches.forEach { branch ->
                        val checked = selected.contains(branch.id)
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(14.dp))
                                .background(if (checked) Palette.Purple100 else Color.White)
                                .clickable {
                                    selected = if (checked) selected - branch.id else selected + branch.id
                                }
                                .padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            Text(if (checked) "☑" else "☐", color = Palette.Purple700)
                            Text(branch.name, style = MaterialTheme.typography.bodyMedium, color = Palette.Indigo950)
                        }
                    }
                }
                GradientButton(
                    text = if (busy) "در حال ساخت…" else "ساخت حساب",
                    enabled = valid && !busy,
                    onClick = { onCreate(fullName.trim(), username.trim(), password, selected) },
                )
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("انصراف", color = Palette.TextMuted) }
        },
    )
}

@Composable
private fun DashboardCard(dashboard: DashboardOut?) {
    GlassCard {
        Text("امروز", style = MaterialTheme.typography.titleMedium, color = Palette.Indigo950)
        if (dashboard == null) {
            Text("در حال بارگذاری…", style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
            return@GlassCard
        }
        Text(
            DateFmt.jalaliDate(dashboard.date),
            style = MaterialTheme.typography.bodyMedium,
            color = Palette.TextMuted,
        )
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Metric("کارمندان", dashboard.active_employees, Palette.Indigo950, Modifier.weight(1f))
            Metric("حاضر", dashboard.present_today, Palette.Emerald600, Modifier.weight(1f))
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Metric("غایب", dashboard.absent_today, Palette.Rose600, Modifier.weight(1f))
            Metric("مرخصی", dashboard.leave_today, Palette.Purple700, Modifier.weight(1f))
        }
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Metric("در انتظار مرخصی", dashboard.pending_leaves, Palette.Gold600, Modifier.weight(1f))
            Metric("در انتظار خروج", dashboard.pending_late_checkouts, Palette.Gold600, Modifier.weight(1f))
        }
        Text(
            "هم‌اکنون در محل کار: ${DateFmt.fa(dashboard.open_check_ins.toString())} نفر",
            style = MaterialTheme.typography.bodyMedium,
            color = Palette.Indigo950,
        )
    }
}

@Composable
private fun Metric(label: String, value: Int, color: Color, modifier: Modifier) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(16.dp))
            .background(Color.White.copy(alpha = 0.6f))
            .padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Text(DateFmt.fa(value.toString()), style = MaterialTheme.typography.titleLarge, color = color)
        Text(label, style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
    }
}

@Composable
private fun DecisionRow(busy: Boolean, onApprove: () -> Unit, onReject: () -> Unit) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Box(
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(14.dp))
                .background(if (busy) Palette.Emerald600.copy(alpha = 0.5f) else Palette.Emerald600)
                .clickable(enabled = !busy, onClick = onApprove)
                .padding(vertical = 12.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("تایید", style = MaterialTheme.typography.labelLarge, color = Color.White)
        }
        Box(
            modifier = Modifier
                .weight(1f)
                .clip(RoundedCornerShape(14.dp))
                .background(Color.White)
                .clickable(enabled = !busy, onClick = onReject)
                .padding(vertical = 12.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text("رد", style = MaterialTheme.typography.labelLarge, color = Palette.Rose600)
        }
    }
}

@Composable
private fun EmptyCard(text: String) {
    GlassCard {
        Text(text, style = MaterialTheme.typography.bodyMedium, color = Palette.TextMuted)
    }
}

private fun Double.formatCoord(): String = DateFmt.fa("%.5f".format(this))

private fun approvalLabel(status: String): String = when (status) {
    "approved" -> "تایید شد"
    "rejected" -> "رد شد"
    else -> "بدون تصمیم"
}

private fun approvalTone(status: String): StatusTone = when (status) {
    "approved" -> StatusTone.Working
    "rejected" -> StatusTone.Bad
    else -> StatusTone.Neutral
}

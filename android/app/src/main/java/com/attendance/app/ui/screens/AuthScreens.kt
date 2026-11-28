package com.attendance.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import com.attendance.app.ui.components.AuroraBackground
import com.attendance.app.ui.components.GlassCard
import com.attendance.app.ui.components.GradientButton
import com.attendance.app.ui.components.NoticeBanner
import com.attendance.app.ui.theme.Palette

@Composable
private fun VGap(dp: Int) = Spacer(Modifier.height(dp.dp))

@Composable
private fun BrandMark() {
    Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .size(76.dp)
                .background(
                    Brush.linearGradient(listOf(Palette.Gold300, Palette.Gold500, Palette.Gold600)),
                    RoundedCornerShape(24.dp),
                ),
            contentAlignment = Alignment.Center,
        ) {
            Text("ح", style = MaterialTheme.typography.displaySmall, color = Color(0xFF3B2A04))
        }
        VGap(12)
        Text("حضور و غیاب", style = MaterialTheme.typography.headlineSmall, color = Palette.Purple800)
    }
}

@Composable
fun GlassField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    password: Boolean = false,
    ltr: Boolean = false,
    modifier: Modifier = Modifier,
) {
    val field: @Composable () -> Unit = {
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            label = { Text(label) },
            singleLine = true,
            modifier = modifier.fillMaxWidth(),
            shape = RoundedCornerShape(18.dp),
            visualTransformation = if (password) PasswordVisualTransformation() else VisualTransformation.None,
            keyboardOptions = KeyboardOptions(
                keyboardType = if (password) KeyboardType.Password else KeyboardType.Text,
            ),
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
    if (ltr) {
        androidx.compose.runtime.CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Ltr) { field() }
    } else {
        field()
    }
}

/** Hides the technical part of the address so the dropdown stays readable. */
internal fun prettyServer(url: String): String =
    url.removePrefix("https://")
        .removePrefix("http://")
        .removeSuffix("api/v1/")
        .trimEnd('/')
        .ifBlank { url }

/**
 * Server address as a fixed dropdown: the user only picks a saved address, so nobody has to type
 * the URL again. A new address can still be added when the network changes.
 */
@Composable
private fun ServerSelector(
    options: List<String>,
    selected: String,
    onSelect: (String) -> Unit,
    onAdd: (String) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    var adding by rememberSaveable { mutableStateOf(false) }
    var newServer by rememberSaveable { mutableStateOf("") }
    val shape = RoundedCornerShape(18.dp)
    val list = (options + selected).filter { it.isNotBlank() }.distinct()

    Box(Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(shape)
                .background(Color.White)
                .border(1.dp, Palette.Purple200, shape)
                .clickable { expanded = true }
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(2.dp),
        ) {
            Text("آدرس سرور", style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    prettyServer(selected),
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.Indigo950,
                )
                Text("تغییر ▾", style = MaterialTheme.typography.labelSmall, color = Palette.Purple600)
            }
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            list.forEach { option ->
                DropdownMenuItem(
                    text = { Text(prettyServer(option)) },
                    onClick = {
                        expanded = false
                        onSelect(option)
                    },
                )
            }
            DropdownMenuItem(
                text = { Text("افزودن آدرس جدید…", color = Palette.Purple600) },
                onClick = {
                    expanded = false
                    adding = true
                },
            )
        }
    }

    if (adding) {
        GlassField(
            newServer,
            { newServer = it },
            "آدرس سرور جدید (مثلاً 192.168.1.10:8000)",
            ltr = true,
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            GradientButton(
                text = "ذخیره و انتخاب",
                gold = true,
                enabled = newServer.isNotBlank(),
                onClick = {
                    onAdd(newServer)
                    newServer = ""
                    adding = false
                },
                modifier = Modifier.weight(1f),
            )
            Text(
                "انصراف",
                style = MaterialTheme.typography.labelLarge,
                color = Palette.TextMuted,
                modifier = Modifier
                    .align(Alignment.CenterVertically)
                    .clickable {
                        adding = false
                        newServer = ""
                    }
                    .padding(horizontal = 8.dp, vertical = 12.dp),
            )
        }
    }
}

@Composable
fun LoginScreen(
    busy: Boolean,
    notice: String?,
    noticeIsError: Boolean,
    serverUrl: String,
    serverOptions: List<String>,
    onLogin: (String, String, String) -> Unit,
    onServerSelected: (String) -> Unit,
) {
    var username by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var server by rememberSaveable(serverUrl) { mutableStateOf(serverUrl) }

    AuroraBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 40.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            BrandMark()
            VGap(28)
            GlassCard(strong = true) {
                Text("ورود به حساب", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                Text(
                    "نام کاربری و رمز عبور را از مدیر خود دریافت کنید.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.TextMuted,
                )
                if (notice != null) NoticeBanner(notice, noticeIsError)
                GlassField(username, { username = it }, "نام کاربری", ltr = true)
                GlassField(password, { password = it }, "رمز عبور", password = true, ltr = true)
                ServerSelector(
                    options = serverOptions,
                    selected = server,
                    onSelect = {
                        server = it
                        onServerSelected(it)
                    },
                    onAdd = {
                        server = it
                        onServerSelected(it)
                    },
                )
                Text(
                    "آدرس سرور ثابت است و روی همین گوشی ذخیره می‌شود؛ نیازی به وارد کردن دوباره آن نیست.",
                    style = MaterialTheme.typography.labelSmall,
                    color = Palette.TextMuted,
                )
                GradientButton(
                    text = if (busy) "در حال ورود…" else "ورود",
                    onClick = { onLogin(username, password, server) },
                    enabled = !busy && username.isNotBlank() && password.isNotBlank() && server.isNotBlank(),
                )
            }
        }
    }
}

@Composable
fun ChangePasswordScreen(
    busy: Boolean,
    notice: String?,
    noticeIsError: Boolean,
    onSubmit: (String, String) -> Unit,
) {
    var current by rememberSaveable { mutableStateOf("") }
    var new by rememberSaveable { mutableStateOf("") }
    var confirm by rememberSaveable { mutableStateOf("") }

    val mismatch = confirm.isNotEmpty() && new != confirm
    val tooShort = new.isNotEmpty() && new.length < 8
    val canSubmit = !busy && current.isNotEmpty() && new.length >= 8 && new == confirm

    AuroraBackground {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 40.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            BrandMark()
            VGap(28)
            GlassCard(strong = true) {
                Text("تغییر رمز عبور", style = MaterialTheme.typography.titleLarge, color = Palette.Indigo950)
                Text(
                    "برای امنیت حساب، پیش از ادامه رمز عبور خود را تغییر دهید.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Palette.TextMuted,
                )
                if (notice != null) NoticeBanner(notice, noticeIsError)
                GlassField(current, { current = it }, "رمز عبور فعلی (اولیه)", password = true, ltr = true)
                GlassField(new, { new = it }, "رمز عبور جدید (حداقل ۸ نویسه)", password = true, ltr = true)
                GlassField(confirm, { confirm = it }, "تکرار رمز عبور جدید", password = true, ltr = true)
                if (tooShort) NoticeBanner("رمز عبور باید حداقل ۸ نویسه باشد.", isError = true)
                if (mismatch) NoticeBanner("تکرار رمز عبور یکسان نیست.", isError = true)
                GradientButton(
                    text = if (busy) "در حال ذخیره…" else "ذخیره و ادامه",
                    onClick = { onSubmit(current, new) },
                    enabled = canSubmit,
                    gold = true,
                )
            }
        }
    }
}

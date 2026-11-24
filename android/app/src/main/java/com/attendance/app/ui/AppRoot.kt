package com.attendance.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.attendance.app.ui.components.AuroraBackground
import com.attendance.app.ui.screens.AdminScreen
import com.attendance.app.ui.screens.ChangePasswordScreen
import com.attendance.app.ui.screens.HomeScreen
import com.attendance.app.ui.screens.LoginScreen
import com.attendance.app.ui.screens.RequestsScreen
import com.attendance.app.ui.screens.WeekScreen
import com.attendance.app.ui.theme.Palette

/** Chooses the screen from the ViewModel state: loading, login, forced password change, or the main app. */
@Composable
fun AppRoot(vm: AppViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()

    when (state.screen) {
        Screen.Loading -> AuroraBackground {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = Palette.Purple600)
            }
        }
        Screen.Login -> LoginScreen(
            busy = state.busy,
            notice = state.notice,
            noticeIsError = state.noticeIsError,
            serverUrl = state.serverUrl,
            serverOptions = state.serverOptions,
            onLogin = vm::login,
            onServerSelected = vm::saveServer,
        )
        Screen.ChangePassword -> ChangePasswordScreen(
            busy = state.busy,
            notice = state.notice,
            noticeIsError = state.noticeIsError,
            onSubmit = vm::changePassword,
        )
        Screen.Main -> MainShell(state, vm)
    }
}

@Composable
private fun MainShell(state: UiState, vm: AppViewModel) {
    var tab by rememberSaveable { mutableIntStateOf(0) }
    val isAdmin = state.me?.role == "admin"
    val tabs = if (isAdmin) {
        listOf("حضور" to 0, "هفته" to 1, "درخواست‌ها" to 2, "مدیریت" to 3)
    } else {
        listOf("حضور" to 0, "هفته" to 1, "درخواست‌ها" to 2)
    }

    // Load whatever the selected tab shows; the ViewModel keeps it in one state object.
    LaunchedEffect(tab) {
        when (tab) {
            1 -> vm.loadWeek()
            2 -> {
                vm.loadMyLeaves()
                vm.loadMyLateCheckouts()
            }
            3 -> vm.loadAdmin(0)
        }
    }

    AuroraBackground {
        Column(Modifier.fillMaxSize().statusBarsPadding()) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text("حضوریار", style = MaterialTheme.typography.titleMedium, color = Palette.Purple800)
                    Text(state.me?.username.orEmpty(), style = MaterialTheme.typography.labelSmall, color = Palette.TextMuted)
                }
                TextButton(onClick = vm::logout) {
                    Text("خروج", color = Palette.Rose600)
                }
            }

            Box(Modifier.weight(1f).fillMaxWidth()) {
                when (tab) {
                    0 -> HomeScreen(
                        userName = state.me?.full_name.orEmpty(),
                        today = state.today,
                        busy = state.busy,
                        notice = state.notice,
                        noticeIsError = state.noticeIsError,
                        onAction = vm::performAction,
                        modifier = Modifier.fillMaxSize(),
                    )
                    1 -> WeekScreen(
                        week = state.week,
                        onLoad = { start -> vm.loadWeek(start) },
                        modifier = Modifier.fillMaxSize(),
                    )
                    2 -> RequestsScreen(
                        leaves = state.leaves,
                        lateCheckouts = state.lateCheckouts,
                        fixReady = state.fix != null,
                        busy = state.busy,
                        notice = state.notice,
                        noticeIsError = state.noticeIsError,
                        onSubmitLeave = { start, end, reason -> vm.submitLeave(start, end, reason) },
                        onFetchLocation = { vm.fetchLocation() },
                        onSubmitLateCheckout = { date, time, description ->
                            vm.submitLateCheckout(date, time, description)
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                    else -> AdminScreen(
                        dashboard = state.adminDashboard,
                        leaves = state.adminLeaves,
                        lateCheckouts = state.adminLateCheckouts,
                        records = state.adminAttendance,
                        branches = state.adminBranches,
                        employees = state.adminEmployees,
                        busy = state.busy,
                        notice = state.notice,
                        noticeIsError = state.noticeIsError,
                        onLoad = vm::loadAdmin,
                        onDecideLeave = { id, decision -> vm.adminDecideLeave(id, decision, null) },
                        onDecideLateCheckout = { id, decision ->
                            vm.adminDecideLateCheckout(id, decision, null)
                        },
                        onDecideAttendance = { id, decision ->
                            vm.adminDecideAttendance(id, decision, null)
                        },
                        onCreateBranch = { name, address, lat, lng, radius ->
                            vm.adminCreateBranch(name, address, lat, lng, radius)
                        },
                        onDeleteBranch = { id -> vm.adminDeleteBranch(id) },
                        onCreateEmployee = { name, username, password, branchIds ->
                            vm.adminCreateEmployee(name, username, password, branchIds)
                        },
                        onSetEmployeeActive = { id, active -> vm.adminSetEmployeeActive(id, active) },
                        onDeleteEmployee = { id -> vm.adminDeleteEmployee(id) },
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            }

            BottomTabs(
                items = tabs,
                selected = tab,
                onSelect = { tab = it },
                modifier = Modifier
                    .navigationBarsPadding()
                    .padding(horizontal = 16.dp, vertical = 12.dp),
            )
        }
    }
}

@Composable
private fun BottomTabs(
    items: List<Pair<String, Int>>,
    selected: Int,
    onSelect: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(26.dp))
            .background(Color.White.copy(alpha = 0.8f))
            .padding(6.dp),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        items.forEach { (label, index) ->
            val active = selected == index
            Box(
                modifier = Modifier
                    .weight(1f)
                    .clip(RoundedCornerShape(20.dp))
                    .background(
                        if (active) {
                            Brush.linearGradient(listOf(Palette.Purple500, Palette.Purple800))
                        } else {
                            Brush.linearGradient(listOf(Color.Transparent, Color.Transparent))
                        },
                    )
                    .clickable { onSelect(index) }
                    .padding(vertical = 14.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    text = label,
                    style = MaterialTheme.typography.labelLarge,
                    color = if (active) Color.White else Palette.Purple800,
                )
            }
        }
    }
}

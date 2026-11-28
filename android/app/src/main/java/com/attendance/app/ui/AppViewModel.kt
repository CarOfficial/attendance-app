package com.attendance.app.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.attendance.app.AttendanceApplication
import com.attendance.app.data.AttendanceRecord
import com.attendance.app.data.BranchOut
import com.attendance.app.data.DashboardOut
import com.attendance.app.data.EmployeeOut
import com.attendance.app.data.HourlyLeaveOut
import com.attendance.app.data.LateCheckoutOut
import com.attendance.app.data.LeaveOut
import com.attendance.app.data.Me
import com.attendance.app.data.SummaryOut
import com.attendance.app.data.TodayOut
import com.attendance.app.data.WeekOut
import com.attendance.app.data.normalizeBaseUrl
import com.attendance.app.location.Fix
import com.attendance.app.util.DateFmt
import com.attendance.app.util.toUserMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException
import kotlin.math.roundToInt

enum class Screen { Loading, Login, ChangePassword, Main }

data class UiState(
    val screen: Screen = Screen.Loading,
    val me: Me? = null,
    val today: TodayOut? = null,
    val history: List<AttendanceRecord> = emptyList(),
    val week: WeekOut? = null,
    /** Monthly report for the employee (attendance summary screen). */
    val summary: SummaryOut? = null,
    val leaves: List<LeaveOut> = emptyList(),
    val hourlyLeaves: List<HourlyLeaveOut> = emptyList(),
    val lateCheckouts: List<LateCheckoutOut> = emptyList(),
    val adminHourlyLeaves: List<HourlyLeaveOut> = emptyList(),
    val adminDashboard: DashboardOut? = null,
    val adminLeaves: List<LeaveOut> = emptyList(),
    val adminLateCheckouts: List<LateCheckoutOut> = emptyList(),
    val adminAttendance: List<AttendanceRecord> = emptyList(),
    val adminBranches: List<BranchOut> = emptyList(),
    val adminEmployees: List<EmployeeOut> = emptyList(),
    /** Last GPS fix obtained through the "get location" button (forgotten check-out form). */
    val fix: Fix? = null,
    /** Server address shown on the login screen; saved in DataStore. */
    val serverUrl: String = "",
    /** Fixed list of server addresses offered in the login dropdown. */
    val serverOptions: List<String> = emptyList(),
    val busy: Boolean = false,
    val notice: String? = null,
    val noticeIsError: Boolean = false,
)

class AppViewModel(application: Application) : AndroidViewModel(application) {

    private val container = application as AttendanceApplication
    private val repo = container.repository
    private val location = container.location

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            container.tokenStore.load()
            _state.update {
                it.copy(
                    serverUrl = container.tokenStore.baseUrl,
                    serverOptions = container.tokenStore.servers,
                )
            }
            if (container.tokenStore.token == null) {
                _state.update { it.copy(screen = Screen.Login) }
            } else {
                enterApp()
            }
        }
    }

    fun clearNotice() = _state.update { it.copy(notice = null) }

    fun login(username: String, password: String, serverUrl: String) {
        val base = normalizeBaseUrl(serverUrl)
        if (base == null) {
            _state.update { it.copy(notice = "آدرس سرور را وارد کنید.", noticeIsError = true) }
            return
        }
        launchBusy(
            onError = { e ->
                val msg = if (e is HttpException && e.code() == 401) {
                    "نام کاربری یا رمز عبور اشتباه است."
                } else {
                    e.toUserMessage()
                }
                _state.update { it.copy(notice = msg, noticeIsError = true) }
            },
        ) {
            container.tokenStore.saveBaseUrl(base)
            repo.reloadApi()
            _state.update { it.copy(serverUrl = base, serverOptions = container.tokenStore.servers) }
            repo.login(username.trim(), password)
            enterApp()
        }
    }

    /** Selects one of the fixed server addresses from the login dropdown and remembers it. */
    fun saveServer(raw: String) {
        val base = normalizeBaseUrl(raw)
        if (base == null) {
            _state.update { it.copy(notice = "آدرس سرور معتبر نیست.", noticeIsError = true) }
            return
        }
        viewModelScope.launch {
            container.tokenStore.saveBaseUrl(base)
            repo.reloadApi()
            _state.update {
                it.copy(
                    serverUrl = base,
                    serverOptions = container.tokenStore.servers,
                    notice = "آدرس سرور ذخیره شد.",
                    noticeIsError = false,
                )
            }
        }
    }

    fun changePassword(current: String, new: String) = launchBusy(
        onError = { e -> _state.update { it.copy(notice = e.toUserMessage(), noticeIsError = true) } },
    ) {
        repo.changePassword(current, new)
        enterApp()
    }

    fun refresh() = launchBusy { loadData() }

    /** Check-in, or check-out with the required daily work description (contract §2). */
    fun performAction(checkIn: Boolean, workDescription: String? = null) = launchBusy {
        val fix = location.currentFix()
        if (checkIn) {
            repo.checkIn(fix)
        } else {
            repo.checkOut(fix, workDescription.orEmpty().trim())
        }
        loadData()
        notify(if (checkIn) "ورود شما ثبت شد" else "خروج شما ثبت شد", error = false)
    }

    // ---- Week screen (contract §2) ----

    fun loadWeek(start: String? = null) = loadDataQuiet {
        val week = repo.week(start)
        _state.update { it.copy(week = week) }
    }

    // ---- Monthly report / absence reasons ----

    fun loadSummary(
        fromDate: String = DateFmt.jalaliMonthStart(DateFmt.todayIso()),
        toDate: String = DateFmt.todayIso(),
    ) = loadDataQuiet {
        val summary = repo.mySummary(fromDate, toDate)
        _state.update { it.copy(summary = summary) }
    }

    /** The employee explains why they were absent on one day. */
    fun submitAbsenceReason(date: String, reason: String) = launchBusy {
        repo.submitAbsenceReason(date, reason.trim())
        val current = _state.value.summary
        val from = current?.from_date ?: DateFmt.jalaliMonthStart(DateFmt.todayIso())
        val to = current?.to_date ?: DateFmt.todayIso()
        val summary = repo.mySummary(from, to)
        _state.update { it.copy(summary = summary) }
        notify("علت غیاب ثبت شد", error = false)
    }

    // ---- Leaves (contract §3) ----

    fun loadMyLeaves() = loadDataQuiet {
        val leaves = repo.myLeaves()
        _state.update { it.copy(leaves = leaves) }
    }

    fun submitLeave(startDate: String, endDate: String, reason: String) = launchBusy {
        repo.createLeave(startDate, endDate, reason.trim())
        val leaves = repo.myLeaves()
        _state.update { it.copy(leaves = leaves) }
        notify("درخواست مرخصی ثبت شد و در انتظار تایید مدیر است", error = false)
    }

    // ---- Hourly leave ----

    fun loadMyHourlyLeaves() = loadDataQuiet {
        val list = repo.myHourlyLeaves()
        _state.update { it.copy(hourlyLeaves = list) }
    }

    fun submitHourlyLeave(date: String, startHour: Double, endHour: Double, reason: String) = launchBusy {
        repo.createHourlyLeave(date, startHour, endHour, reason.trim())
        val list = repo.myHourlyLeaves()
        _state.update { it.copy(hourlyLeaves = list) }
        notify("درخواست مرخصی ساعتی ثبت شد و در انتظار تایید مدیر است", error = false)
    }

    // ---- Forgotten check-out (contract §2) ----

    fun loadMyLateCheckouts() = loadDataQuiet {
        val list = repo.myLateCheckouts()
        _state.update { it.copy(lateCheckouts = list) }
    }

    /** One GPS fix for the forgotten check-out form. The UI must hold the permission. */
    fun fetchLocation() = launchBusy {
        val fix = location.currentFix()
        _state.update { it.copy(fix = fix) }
        val accuracy = DateFmt.fa(fix.accuracyM.roundToInt().toString())
        notify("موقعیت مکانی دریافت شد (دقت $accuracy متر)", error = false)
    }

    fun submitLateCheckout(workDate: String, checkOutTime: String, description: String) = launchBusy {
        val fix = _state.value.fix ?: location.currentFix()
        repo.lateCheckout(workDate, checkOutTime, fix, description.trim())
        val list = repo.myLateCheckouts()
        _state.update { it.copy(lateCheckouts = list) }
        notify("درخواست ثبت خروج فراموش‌شده ثبت شد", error = false)
    }

    // ---- Admin (contract §4) ----

    /**
     * section: 0 = dashboard, 1 = leaves, 2 = late check-outs, 3 = attendance,
     * 4 = offices, 5 = employee accounts.
     */
    fun loadAdmin(section: Int) = loadDataQuiet { adminData(section) }

    private suspend fun adminData(section: Int) {
        when (section) {
            0 -> {
                val dashboard = repo.adminDashboard()
                _state.update { it.copy(adminDashboard = dashboard) }
            }
            1 -> {
                val leaves = repo.adminLeaves(status = "pending", limit = 100)
                _state.update { it.copy(adminLeaves = leaves) }
            }
            2 -> {
                val list = repo.adminLateCheckouts(status = "pending", limit = 100)
                _state.update { it.copy(adminLateCheckouts = list) }
            }
            3 -> {
                val list = repo.adminAttendance(limit = 50)
                _state.update { it.copy(adminAttendance = list) }
            }
            4 -> {
                val branches = repo.adminBranches()
                _state.update { it.copy(adminBranches = branches) }
            }
            5 -> {
                val employees = repo.adminEmployees()
                _state.update { it.copy(adminEmployees = employees) }
            }
            else -> {
                val list = repo.adminHourlyLeaves(status = "pending", limit = 100)
                _state.update { it.copy(adminHourlyLeaves = list) }
            }
        }
    }

    fun adminCreateBranch(
        name: String,
        address: String?,
        latitude: Double,
        longitude: Double,
        radiusM: Double,
    ) = launchBusy {
        repo.createBranch(name, address, latitude, longitude, radiusM)
        adminData(4)
        notify("دفتر جدید ثبت شد", error = false)
    }

    fun adminDeleteBranch(id: Int) = launchBusy {
        repo.deleteBranch(id)
        adminData(4)
        notify("دفتر حذف شد", error = false)
    }

    fun adminCreateEmployee(
        fullName: String,
        username: String,
        password: String,
        branchIds: List<Int>,
    ) = launchBusy {
        repo.createEmployee(fullName, username, password, branchIds)
        adminData(5)
        notify("حساب کارمند ساخته شد", error = false)
    }

    fun adminSetEmployeeActive(id: Int, active: Boolean) = launchBusy {
        repo.setEmployeeActive(id, active)
        adminData(5)
        notify(if (active) "حساب فعال شد" else "حساب غیرفعال شد", error = false)
    }

    fun adminDeleteEmployee(id: Int) = launchBusy {
        repo.deleteEmployee(id)
        adminData(5)
        notify("حساب کارمند حذف شد", error = false)
    }

    fun adminDecideLeave(id: Int, decision: String, note: String?) = launchBusy {
        repo.decideLeave(id, decision, note)
        val leaves = repo.adminLeaves(status = "pending", limit = 100)
        _state.update { it.copy(adminLeaves = leaves) }
        notify(if (decision == "approve") "مرخصی تایید شد" else "مرخصی رد شد", error = false)
    }

    fun adminDecideHourlyLeave(id: Int, decision: String, note: String?) = launchBusy {
        repo.decideHourlyLeave(id, decision, note)
        val list = repo.adminHourlyLeaves(status = "pending", limit = 100)
        _state.update { it.copy(adminHourlyLeaves = list) }
        notify(if (decision == "approve") "مرخصی ساعتی تایید شد" else "مرخصی ساعتی رد شد", error = false)
    }

    /** Admin records an employee's check-in/check-out manually (no GPS needed). */
    fun adminManualAttendance(
        userId: Int,
        branchId: Int,
        workDate: String,
        checkIn: String,
        checkOut: String?,
        description: String?,
    ) = launchBusy {
        repo.adminManualAttendance(userId, branchId, workDate, checkIn, checkOut, description)
        val list = repo.adminAttendance(limit = 50)
        _state.update { it.copy(adminAttendance = list) }
        notify("حضور دستی ثبت شد", error = false)
    }

    fun adminDecideLateCheckout(id: Int, decision: String, note: String?) = launchBusy {
        repo.decideLateCheckout(id, decision, note)
        val list = repo.adminLateCheckouts(status = "pending", limit = 100)
        _state.update { it.copy(adminLateCheckouts = list) }
        notify(if (decision == "approve") "خروج فراموش‌شده تایید شد" else "درخواست رد شد", error = false)
    }

    fun adminDecideAttendance(id: Int, decision: String, note: String?) = launchBusy {
        repo.decideAttendance(id, decision, note)
        val list = repo.adminAttendance(limit = 50)
        _state.update { it.copy(adminAttendance = list) }
        notify(if (decision == "approve") "رکورد تایید شد" else "رکورد رد شد", error = false)
    }

    fun logout() = launchBusy {
        repo.logout()
        _state.value = UiState(screen = Screen.Login)
    }

    /** Fetches the profile and chooses the screen. Called after login, password change and app start. */
    private suspend fun enterApp() {
        try {
            val me = repo.me()
            if (me.must_change_password) {
                _state.update { it.copy(screen = Screen.ChangePassword, me = me) }
            } else {
                _state.update { it.copy(screen = Screen.Main, me = me) }
                loadData()
            }
        } catch (e: Throwable) {
            handleFailure(e)
        }
    }

    private suspend fun loadData() {
        val today = repo.today()
        val history = repo.history()
        _state.update { it.copy(today = today, history = history) }
    }

    private suspend fun handleFailure(e: Throwable) {
        if (e is HttpException && e.code() == 401) {
            repo.logout()
            _state.value = UiState(screen = Screen.Login, notice = e.toUserMessage(), noticeIsError = true)
        } else {
            _state.update {
                it.copy(
                    screen = if (it.screen == Screen.Loading) Screen.Login else it.screen,
                    notice = e.toUserMessage(),
                    noticeIsError = true,
                )
            }
        }
    }

    private fun notify(text: String, error: Boolean) =
        _state.update { it.copy(notice = text, noticeIsError = error) }

    /** Runs one action at a time; clears the notice first and reports errors in Persian. */
    private fun launchBusy(
        onError: suspend (Throwable) -> Unit = { handleFailure(it) },
        block: suspend () -> Unit,
    ) {
        if (_state.value.busy) return
        viewModelScope.launch {
            _state.update { it.copy(busy = true, notice = null) }
            try {
                block()
            } catch (e: Throwable) {
                onError(e)
            } finally {
                _state.update { it.copy(busy = false) }
            }
        }
    }

    /** Loads screen data without the global busy flag, so screens can refresh independently. */
    private fun loadDataQuiet(block: suspend () -> Unit) {
        viewModelScope.launch {
            try {
                block()
            } catch (e: Throwable) {
                handleFailure(e)
            }
        }
    }
}

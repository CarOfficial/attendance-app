package com.attendance.app.data

import com.attendance.app.location.Fix

class AttendanceRepository(private val tokens: TokenStore) {

    @Volatile
    private var client: AttendanceApi? = null

    /** Created on first use, so the saved server address is always the one in effect. */
    private val api: AttendanceApi
        get() = client ?: synchronized(this) {
            client ?: createApi(tokens.baseUrl, tokens).also { client = it }
        }

    /** Drops the current client so the next call uses the newly saved server address. */
    fun reloadApi() {
        client = null
    }

    suspend fun login(username: String, password: String): TokenOut {
        val out = api.login(LoginBody(username, password))
        tokens.save(out.access_token)
        return out
    }

    suspend fun changePassword(current: String, new: String): TokenOut {
        val out = api.changePassword(ChangePasswordBody(current, new))
        tokens.save(out.access_token)
        return out
    }

    suspend fun me(): Me = api.me()

    suspend fun today(): TodayOut = api.today()

    suspend fun checkIn(fix: Fix): AttendanceRecord = api.checkIn(fix.toBody())

    /** Check-out requires the daily work description (contract §2). */
    suspend fun checkOut(fix: Fix, workDescription: String): AttendanceRecord =
        api.checkOut(
            CheckOutBody(
                latitude = fix.latitude,
                longitude = fix.longitude,
                accuracy_m = fix.accuracyM,
                work_description = workDescription,
            ),
        )

    suspend fun history(fromDate: String? = null, toDate: String? = null): List<AttendanceRecord> =
        api.history(fromDate, toDate)

    // ---- Week / forgotten check-out / leaves (contract §2–3) ----

    suspend fun week(start: String? = null): WeekOut = api.week(start)

    suspend fun lateCheckout(
        workDate: String,
        checkOutTime: String,
        fix: Fix,
        description: String,
    ): LateCheckoutOut = api.lateCheckout(
        LateCheckoutIn(
            work_date = workDate,
            check_out_time = checkOutTime,
            latitude = fix.latitude,
            longitude = fix.longitude,
            accuracy_m = fix.accuracyM,
            description = description,
        ),
    )

    suspend fun myLateCheckouts(): List<LateCheckoutOut> = api.lateCheckoutsMine()

    suspend fun createLeave(startDate: String, endDate: String, reason: String): LeaveOut =
        api.createLeave(LeaveIn(startDate, endDate, reason))

    suspend fun myLeaves(): List<LeaveOut> = api.leavesMine()

    // ---- Admin (contract §4) ----

    suspend fun adminDashboard(): DashboardOut = api.adminDashboard()

    suspend fun adminAttendance(limit: Int? = null): List<AttendanceRecord> =
        api.adminAttendance(limit = limit)

    suspend fun decideAttendance(id: Int, decision: String, note: String?): AttendanceDecisionOut =
        api.adminAttendanceDecision(id, DecisionIn(decision, note))

    suspend fun adminLeaves(status: String? = null, limit: Int? = null): List<LeaveOut> =
        api.adminLeaves(status, limit = limit)

    suspend fun decideLeave(id: Int, decision: String, note: String?): LeaveOut =
        api.adminLeaveDecision(id, DecisionIn(decision, note))

    suspend fun adminLateCheckouts(status: String? = null, limit: Int? = null): List<LateCheckoutOut> =
        api.adminLateCheckouts(status, limit = limit)

    suspend fun decideLateCheckout(id: Int, decision: String, note: String?): LateCheckoutOut =
        api.adminLateCheckoutDecision(id, DecisionIn(decision, note))

    // ---- Admin: offices and employee accounts ----

    suspend fun adminBranches(): List<BranchOut> = api.adminBranches()

    suspend fun createBranch(
        name: String,
        address: String?,
        latitude: Double,
        longitude: Double,
        radiusM: Double,
    ): BranchOut = api.adminCreateBranch(
        BranchIn(
            name = name.trim(),
            address = address?.trim()?.ifEmpty { null },
            latitude = latitude,
            longitude = longitude,
            radius_m = radiusM,
        ),
    )

    suspend fun deleteBranch(id: Int) = api.adminDeleteBranch(id, force = true)

    suspend fun adminEmployees(): List<EmployeeOut> = api.adminEmployees()

    suspend fun createEmployee(
        fullName: String,
        username: String,
        password: String,
        branchIds: List<Int>,
    ): EmployeeOut = api.adminCreateEmployee(
        EmployeeCreateBody(
            username = username.trim(),
            full_name = fullName.trim(),
            password = password,
            branch_ids = branchIds,
        ),
    )

    suspend fun setEmployeeActive(id: Int, active: Boolean): EmployeeOut =
        api.adminUpdateEmployee(id, EmployeePatchBody(active))

    suspend fun deleteEmployee(id: Int) = api.adminDeleteEmployee(id, force = true)

    suspend fun logout() = tokens.save(null)

    private fun Fix.toBody() = LocationBody(latitude, longitude, accuracyM)
}

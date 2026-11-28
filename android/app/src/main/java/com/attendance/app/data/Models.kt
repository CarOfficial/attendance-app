package com.attendance.app.data

// Field names match the API's snake_case JSON so Gson maps them directly.

data class TokenOut(
    val access_token: String,
    val token_type: String,
    val must_change_password: Boolean,
)

data class Me(
    val id: Int,
    val username: String,
    val full_name: String,
    val role: String,
    val is_active: Boolean,
    val must_change_password: Boolean,
    val branch_ids: List<Int>,
)

data class AttendanceRecord(
    val id: Int,
    val user_id: Int,
    val user_full_name: String,
    val work_date: String,
    val branch_id: Int,
    val branch_name: String,
    val check_in_at: String,
    val check_out_at: String?,
    val edited_by_admin: Boolean,
    // AttendanceOut extras (contract §2).
    val work_description: String? = null,
    val check_out_source: String? = null, // employee | late | admin | null
    val approval_status: String = "none", // none | approved | rejected
    val approval_note: String? = null,
    val hours_worked: Double? = null,
    val late_minutes: Int = 0,
    val overtime_minutes: Int = 0,
    val check_in_edited: Boolean = false,
    val check_out_edited: Boolean = false,
)

data class TodayOut(
    val status: String, // not_checked_in | checked_in | checked_out
    val record: AttendanceRecord?,
)

/** A day of the week report (contract §2 DayStateOut). */
data class DayStateOut(
    val date: String, // yyyy-MM-dd
    val is_work_day: Boolean = true,
    val status: String = "", // see the contract §2 status table
    val check_in_at: String? = null,
    val check_out_at: String? = null,
    val hours_worked: Double? = null,
    val branch_name: String? = null,
    val work_description: String? = null,
    val approval_status: String = "none",
    val approval_note: String? = null,
    val late_request_status: String? = null, // pending | approved | rejected | expired
    val pending_leave: Boolean = false,
    val is_late: Boolean = false,
    val left_early: Boolean = false,
    val hourly_leave_hours: Double = 0.0,
    val late_minutes: Int = 0,
    val overtime_minutes: Int = 0,
    val absence_reason: String? = null,
)

/** GET /attendance/summary totals for one employee. */
data class SummaryTotalsOut(
    val present: Int = 0,
    val absent: Int = 0,
    val leave: Int = 0,
    val pending_checkout: Int = 0,
    val non_working: Int = 0,
    val future: Int = 0,
    val total_hours: Double = 0.0,
    val late_count: Int = 0,
    val early_leave_count: Int = 0,
    val late_minutes: Int = 0,
    val overtime_minutes: Int = 0,
)

data class SummaryOut(
    val user_id: Int,
    val user_full_name: String,
    val from_date: String,
    val to_date: String,
    val days: List<DayStateOut> = emptyList(),
    val totals: SummaryTotalsOut = SummaryTotalsOut(),
)

/** POST /attendance/absence-reason */
data class AbsenceReasonBody(val date: String, val reason: String)

data class AbsenceReasonOut(
    val id: Int,
    val user_id: Int,
    val date: String,
    val reason: String,
    val created_at: String? = null,
)

data class ScheduleOut(
    val work_days: List<Int> = emptyList(), // 0=دوشنبه … 6=یکشنبه؛ 5=شنبه
    val start_time: String = "",
    val end_time: String = "",
    val late_grace_minutes: Int = 0,
    val updated_at: String? = null,
)

data class WeekOut(
    val start: String,
    val end: String,
    val days: List<DayStateOut>,
    val schedule: ScheduleOut,
)

/** A forgotten check-out request (contract §2 LateCheckoutOut). */
data class LateCheckoutOut(
    val id: Int,
    val user_id: Int,
    val user_full_name: String,
    val work_date: String,
    val record_id: Int,
    val requested_at: String? = null,
    val check_out_at: String? = null, // ISO datetime of the claimed check-out
    val description: String? = null,
    val status: String = "pending", // pending | approved | rejected | expired
    val branch_name: String? = null,
    val distance_m: Double? = null,
    val decided_at: String? = null,
    val decision_note: String? = null,
    val submission_deadline: String? = null,
    val decision_deadline: String? = null,
)

/** A leave request (contract §3 LeaveOut). */
data class LeaveOut(
    val id: Int,
    val user_id: Int,
    val user_full_name: String,
    val start_date: String,
    val end_date: String,
    val reason: String,
    val status: String = "pending", // pending | approved | rejected
    val created_at: String? = null,
    val decided_at: String? = null,
    val decision_note: String? = null,
)

/** Hourly leave (a few hours off on one day). */
data class HourlyLeaveOut(
    val id: Int,
    val user_id: Int,
    val user_full_name: String,
    val date: String,
    val start_hour: Double,
    val end_hour: Double,
    val reason: String,
    val status: String = "pending", // pending | approved | rejected
    val created_at: String? = null,
    val decided_at: String? = null,
    val decided_by: Int? = null,
    val decision_note: String? = null,
)

data class HourlyLeaveBody(
    val date: String,
    val start_hour: Double,
    val end_hour: Double,
    val reason: String,
    // Only the admin sets this; the employee endpoint always uses the signed-in user.
    val user_id: Int? = null,
)

/** Admin records an employee's check-in (and optional check-out) without GPS. */
data class ManualAttendanceBody(
    val user_id: Int,
    val branch_id: Int,
    val work_date: String? = null,
    val check_in: String,
    val check_out: String? = null,
    val work_description: String? = null,
)

/** Admin dashboard numbers (contract §4). */
data class DashboardOut(
    val date: String,
    val active_employees: Int = 0,
    val present_today: Int = 0,
    val absent_today: Int = 0,
    val leave_today: Int = 0,
    val rejected_today: Int = 0,
    val open_check_ins: Int = 0,
    val pending_leaves: Int = 0,
    val pending_late_checkouts: Int = 0,
    val pending_hourly_leaves: Int = 0,
)

/** Response of PATCH admin/attendance/{id}/decision (contract §4). */
data class AttendanceDecisionOut(
    val id: Int,
    val approval_status: String,
    val approval_note: String? = null,
)

data class LoginBody(val username: String, val password: String)

data class ChangePasswordBody(val current_password: String, val new_password: String)

data class LocationBody(val latitude: Double, val longitude: Double, val accuracy_m: Double)

/** Check-out body: location plus the required daily work description (contract §2). */
data class CheckOutBody(
    val latitude: Double,
    val longitude: Double,
    val accuracy_m: Double,
    val work_description: String,
)

data class LateCheckoutIn(
    val work_date: String,
    val check_out_time: String, // HH:MM
    val latitude: Double,
    val longitude: Double,
    val accuracy_m: Double,
    val description: String,
)

data class LeaveIn(
    val start_date: String,
    val end_date: String,
    val reason: String,
)

/** Office location (contract §4 BranchOut). */
data class BranchOut(
    val id: Int,
    val name: String,
    val address: String? = null,
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val radius_m: Double = 100.0,
    val is_active: Boolean = true,
)

/** Employee account as returned by the admin endpoints (contract §4 UserOut). */
data class EmployeeOut(
    val id: Int,
    val username: String,
    val full_name: String,
    val role: String = "employee",
    val is_active: Boolean = true,
    val must_change_password: Boolean = false,
    val branch_ids: List<Int> = emptyList(),
)

data class BranchIn(
    val name: String,
    val address: String? = null,
    val latitude: Double,
    val longitude: Double,
    val radius_m: Double = 100.0,
    val is_active: Boolean = true,
)

data class EmployeeCreateBody(
    val username: String,
    val full_name: String,
    val password: String,
    val branch_ids: List<Int> = emptyList(),
)

data class EmployeePatchBody(val is_active: Boolean)

/** Approve/reject body shared by the admin decision endpoints (contract §4). */
data class DecisionIn(
    val decision: String, // approve | reject
    val note: String? = null,
)

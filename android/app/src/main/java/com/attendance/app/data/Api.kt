package com.attendance.app.data

import com.google.gson.GsonBuilder
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query
import java.util.concurrent.TimeUnit

interface AttendanceApi {
    @POST("auth/login")
    suspend fun login(@Body body: LoginBody): TokenOut

    @GET("auth/me")
    suspend fun me(): Me

    @POST("auth/change-password")
    suspend fun changePassword(@Body body: ChangePasswordBody): TokenOut

    @GET("attendance/today")
    suspend fun today(): TodayOut

    @POST("attendance/check-in")
    suspend fun checkIn(@Body body: LocationBody): AttendanceRecord

    @POST("attendance/check-out")
    suspend fun checkOut(@Body body: CheckOutBody): AttendanceRecord

    @GET("attendance/history")
    suspend fun history(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null,
    ): List<AttendanceRecord>

    @GET("attendance/week")
    suspend fun week(@Query("start") start: String? = null): WeekOut

    @GET("attendance/summary")
    suspend fun summary(
        @Query("from_date") fromDate: String,
        @Query("to_date") toDate: String,
    ): SummaryOut

    /** The employee explains an absent day (shown to the manager in the panel). */
    @POST("attendance/absence-reason")
    suspend fun createAbsenceReason(@Body body: AbsenceReasonBody): AbsenceReasonOut

    @POST("attendance/late-checkout")
    suspend fun lateCheckout(@Body body: LateCheckoutIn): LateCheckoutOut

    @GET("attendance/late-checkouts")
    suspend fun lateCheckoutsMine(): List<LateCheckoutOut>

    @POST("leaves")
    suspend fun createLeave(@Body body: LeaveIn): LeaveOut

    @GET("leaves/mine")
    suspend fun leavesMine(): List<LeaveOut>

    @POST("leaves/hourly")
    suspend fun createHourlyLeave(@Body body: HourlyLeaveBody): HourlyLeaveOut

    @GET("leaves/hourly/mine")
    suspend fun hourlyLeavesMine(): List<HourlyLeaveOut>

    // ---- Admin (contract §4) ----

    @GET("admin/dashboard")
    suspend fun adminDashboard(): DashboardOut

    @GET("admin/attendance")
    suspend fun adminAttendance(
        @Query("from_date") fromDate: String? = null,
        @Query("to_date") toDate: String? = null,
        @Query("user_id") userId: Int? = null,
        @Query("branch_id") branchId: Int? = null,
        @Query("limit") limit: Int? = null,
        @Query("offset") offset: Int? = null,
    ): List<AttendanceRecord>

    @PATCH("admin/attendance/{id}/decision")
    suspend fun adminAttendanceDecision(
        @Path("id") id: Int,
        @Body body: DecisionIn,
    ): AttendanceDecisionOut

    /** Admin records an employee's check-in/check-out manually (no GPS). */
    @POST("admin/attendance/manual")
    suspend fun adminManualAttendance(@Body body: ManualAttendanceBody): AttendanceRecord

    @GET("admin/hourly-leaves")
    suspend fun adminHourlyLeaves(
        @Query("status") status: String? = null,
        @Query("user_id") userId: Int? = null,
        @Query("limit") limit: Int? = null,
    ): List<HourlyLeaveOut>

    @PATCH("admin/hourly-leaves/{id}")
    suspend fun adminHourlyLeaveDecision(
        @Path("id") id: Int,
        @Body body: DecisionIn,
    ): HourlyLeaveOut

    @GET("admin/leaves")
    suspend fun adminLeaves(
        @Query("status") status: String? = null,
        @Query("user_id") userId: Int? = null,
        @Query("limit") limit: Int? = null,
    ): List<LeaveOut>

    @PATCH("admin/leaves/{id}")
    suspend fun adminLeaveDecision(
        @Path("id") id: Int,
        @Body body: DecisionIn,
    ): LeaveOut

    @GET("admin/late-checkouts")
    suspend fun adminLateCheckouts(
        @Query("status") status: String? = null,
        @Query("user_id") userId: Int? = null,
        @Query("limit") limit: Int? = null,
    ): List<LateCheckoutOut>

    @PATCH("admin/late-checkouts/{id}")
    suspend fun adminLateCheckoutDecision(
        @Path("id") id: Int,
        @Body body: DecisionIn,
    ): LateCheckoutOut

    // ---- Admin: offices and employee accounts ----

    @GET("admin/branches")
    suspend fun adminBranches(): List<BranchOut>

    @POST("admin/branches")
    suspend fun adminCreateBranch(@Body body: BranchIn): BranchOut

    @DELETE("admin/branches/{id}")
    suspend fun adminDeleteBranch(
        @Path("id") id: Int,
        @Query("force") force: Boolean = false,
    )

    @GET("admin/employees")
    suspend fun adminEmployees(): List<EmployeeOut>

    @POST("admin/employees")
    suspend fun adminCreateEmployee(@Body body: EmployeeCreateBody): EmployeeOut

    @PATCH("admin/employees/{id}")
    suspend fun adminUpdateEmployee(
        @Path("id") id: Int,
        @Body body: EmployeePatchBody,
    ): EmployeeOut

    @DELETE("admin/employees/{id}")
    suspend fun adminDeleteEmployee(
        @Path("id") id: Int,
        @Query("force") force: Boolean = false,
    )
}

/**
 * Accepts "server.example", "http://1.2.3.4:8000" or a full ".../api/v1/" address and returns a
 * Retrofit-ready base URL that ends with "/". Null means the input was blank.
 */
fun normalizeBaseUrl(raw: String): String? {
    var url = raw.trim()
    if (url.isEmpty()) return null
    if (!url.startsWith("http://", true) && !url.startsWith("https://", true)) {
        url = "http://$url"
    }
    if (!url.endsWith("/")) url = "$url/"
    if (!url.contains("/api/")) url = "${url}api/v1/"
    return url
}

/** baseUrl must end with "/". Adds the bearer token to every request when one is stored. */
fun createApi(baseUrl: String, tokens: TokenStore): AttendanceApi {
    val client = OkHttpClient.Builder()
        .addInterceptor { chain ->
            val request = chain.request()
            val token = tokens.token
            val authed = if (token != null) {
                request.newBuilder().header("Authorization", "Bearer $token").build()
            } else {
                request
            }
            chain.proceed(authed)
        }
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    val gson = GsonBuilder().create()
    return Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create(gson))
        .build()
        .create(AttendanceApi::class.java)
}

package com.attendance.app

import android.app.Application
import com.attendance.app.data.AttendanceRepository
import com.attendance.app.data.TokenStore
import com.attendance.app.location.LocationProvider

/** Minimal dependency container. Created once per process. */
class AttendanceApplication : Application() {

    val tokenStore: TokenStore by lazy { TokenStore(this) }
    val repository: AttendanceRepository by lazy { AttendanceRepository(tokenStore) }
    val location: LocationProvider by lazy { LocationProvider(this) }
}

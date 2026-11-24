package com.attendance.app.location

import android.annotation.SuppressLint
import android.content.Context
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

data class Fix(val latitude: Double, val longitude: Double, val accuracyM: Double)

class LocationException(message: String) : Exception(message)

class LocationProvider(context: Context) {

    private val client = LocationServices.getFusedLocationProviderClient(context)

    /** One high-accuracy fix. The caller must hold ACCESS_FINE_LOCATION. */
    @SuppressLint("MissingPermission")
    suspend fun currentFix(): Fix = suspendCancellableCoroutine { cont ->
        val cts = CancellationTokenSource()
        cont.invokeOnCancellation { cts.cancel() }
        client.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, cts.token)
            .addOnSuccessListener { loc ->
                if (loc == null) {
                    cont.resumeWithException(LocationException("موقعیت دریافت نشد. کمی صبر کنید و دوباره تلاش کنید."))
                } else {
                    cont.resume(Fix(loc.latitude, loc.longitude, loc.accuracy.toDouble()))
                }
            }
            .addOnFailureListener {
                cont.resumeWithException(LocationException("دریافت موقعیت ممکن نشد. GPS را روشن کنید."))
            }
    }
}

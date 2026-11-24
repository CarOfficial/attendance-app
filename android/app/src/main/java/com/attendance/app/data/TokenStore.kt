package com.attendance.app.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.attendance.app.BuildConfig
import kotlinx.coroutines.flow.first

private val Context.authDataStore: DataStore<Preferences> by preferencesDataStore(name = "auth")

/**
 * Keeps the access token and the server address in DataStore. Copies stay in memory so the
 * OkHttp interceptor and the Retrofit client can read them synchronously.
 */
class TokenStore(private val context: Context) {

    private val key = stringPreferencesKey("access_token")
    private val baseUrlKey = stringPreferencesKey("api_base_url")
    private val serversKey = stringPreferencesKey("api_servers")

    @Volatile
    var token: String? = null
        private set

    /** Effective API base URL: the one the user saved, otherwise the build-time default. */
    @Volatile
    var baseUrl: String = BuildConfig.API_BASE_URL
        private set

    /**
     * The fixed list of server addresses offered in the login dropdown. The build-time default
     * always stays in the list so the app can be pointed at a working server again.
     */
    @Volatile
    var servers: List<String> = listOf(BuildConfig.API_BASE_URL)
        private set

    suspend fun load() {
        val prefs = context.authDataStore.data.first()
        token = prefs[key]
        baseUrl = prefs[baseUrlKey] ?: BuildConfig.API_BASE_URL
        val saved = prefs[serversKey]
            ?.split(SERVER_SEPARATOR)
            ?.map { it.trim() }
            ?.filter { it.isNotEmpty() }
            .orEmpty()
        servers = (saved + baseUrl + BuildConfig.API_BASE_URL).distinct()
    }

    suspend fun save(value: String?) {
        token = value
        context.authDataStore.edit { prefs ->
            if (value == null) prefs.remove(key) else prefs[key] = value
        }
    }

    suspend fun saveBaseUrl(value: String) {
        baseUrl = value
        val updated = (listOf(value) + servers).distinct()
        servers = updated
        context.authDataStore.edit { prefs ->
            prefs[baseUrlKey] = value
            prefs[serversKey] = updated.joinToString(SERVER_SEPARATOR)
        }
    }

    private companion object {
        const val SERVER_SEPARATOR = "\n"
    }
}

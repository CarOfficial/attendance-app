# Android app — حضور و غیاب

Native Kotlin + Jetpack Compose app for employees. Talks to the same API as the PWA.

## Requirements
- Android Studio Koala (2024.1) or newer, JDK 17
- Android SDK 35, minSdk 26 (Android 8.0)
- A running backend (see `../backend/README.md`)

## Build and run (debug, emulator)
1. Start the backend: `cd ../ && docker compose up -d` (API on `127.0.0.1:8000`).
2. Open the `android/` folder in Android Studio and let Gradle sync.
3. If Gradle asks for a wrapper, run once in a terminal inside `android/`:
   `gradle wrapper --gradle-version 8.10.2` (requires a local Gradle install).
4. Run on an emulator. Debug builds call `http://10.0.2.2:8000/api/v1/`, which is the host machine from inside the emulator.

## Run on a physical phone (debug)
Change `API_BASE_URL` in `app/build.gradle.kts` (debug block) to your computer's LAN address, for example `http://192.168.1.20:8000/api/v1/`, and allow cleartext for that host in `res/xml/network_security_config.xml`. Use the phone and computer on the same network.

## Release build
- Set `API_BASE_URL` in the `release` block to your HTTPS domain, for example `https://attendance.example.com/api/v1/`.
- Create a signing key (`keytool`), add a `signingConfigs` block, and build with *Build → Generate Signed Bundle / APK*.
- Cleartext traffic is disabled in release by `network_security_config.xml`.

## Location behaviour
- Check-in and check-out use `FusedLocationProvider` with high accuracy, asking for `ACCESS_FINE_LOCATION` on first use.
- The server decides whether the fix is inside the branch radius. The phone never decides the time or the result.
- If GPS accuracy is poor (over 100 m on the server), the app asks the user to step into the open and try again.
- There is no offline queue: a check-in sent late would record the wrong server time, so the user retries when online.

## Project layout
```
app/src/main/java/com/attendance/app/
  AttendanceApplication.kt   dependency container (token store, repository, location)
  MainActivity.kt            entry point, edge-to-edge, RTL theme
  data/                      Retrofit API, DataStore token store, repository, models
  location/                  FusedLocationProvider wrapper (one high-accuracy fix)
  util/                      Persian error messages, Jalali dates, Persian digits
  ui/theme/                  royal purple / gold palette, Vazirmatn, forced RTL
  ui/components/             aurora background, glass cards, orb button, pills
  ui/screens/                login, forced password change, home, history
  ui/AppViewModel.kt         state and actions
  ui/AppRoot.kt              screen switch and glass bottom tabs
```

## Status
- Kotlin sources were syntax-checked with the Kotlin 2.0.21 compiler. Remaining compiler messages are unresolved Android/Compose/Retrofit symbols, which only resolve with the Android SDK and Maven dependencies.
- The APK has **not** been compiled or run on a device or emulator yet. Expect a short round of compile fixes on the first Android Studio build.

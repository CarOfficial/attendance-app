# Gson reads these models by field name; keep them intact in release builds.
-keep class com.attendance.app.data.** { *; }
-keepattributes Signature, *Annotation*

#!/usr/bin/env bash
# Build the HozoorYar APK against a public API base URL.
#   ./scripts/build_apk.sh https://your-name.ngrok-free.app/api/v1/
# The URL is baked into BuildConfig.API_BASE_URL at compile time.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_BASE_URL="${1:-}"

if [ -z "$API_BASE_URL" ]; then
  echo "usage: $0 <api-base-url>   e.g. https://xxxx.ngrok-free.app/api/v1/" >&2
  exit 2
fi
case "$API_BASE_URL" in
  */) ;;
  *) echo "API base URL must end with '/'" >&2; exit 2 ;;
esac

export JAVA_HOME="$ROOT/.tools/android-build/jdk-17.0.21.1+2"
export ANDROID_HOME="$ROOT/.tools/android-build/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"

cd "$ROOT/android"
"$ROOT/.tools/android-build/gradle-8.7/bin/gradle.bat" assembleDebug --no-daemon \
  -PAPI_BASE_URL="$API_BASE_URL" \
  --init-script "$ROOT/.tools/android-build/mirror.init.gradle"

APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
VERSION="1.0.3"
cp "$APK" "$ROOT/dist/HozoorYar-$VERSION.apk"
echo "built: $ROOT/dist/HozoorYar-$VERSION.apk (API_BASE_URL=$API_BASE_URL)"

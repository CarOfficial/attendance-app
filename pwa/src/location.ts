export interface Fix {
  latitude: number;
  longitude: number;
  accuracy_m: number;
}

export class LocationError extends Error {}

/** Gets a single high-accuracy GPS fix. Rejects with a LocationError that has a Persian message. */
export function getCurrentFix(timeoutMs = 15000): Promise<Fix> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new LocationError("مرورگر شما از موقعیت مکانی پشتیبانی نمی‌کند."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy_m: pos.coords.accuracy,
        }),
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          reject(new LocationError("دسترسی به موقعیت مکانی داده نشده است. از تنظیمات مرورگر یا iPhone اجازه دهید."));
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          reject(new LocationError("موقعیت شما در دسترس نیست. کمی صبر کنید و دوباره تلاش کنید."));
        } else {
          reject(new LocationError("دریافت موقعیت زمان‌بر شد. دوباره تلاش کنید."));
        }
      },
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 0 },
    );
  });
}

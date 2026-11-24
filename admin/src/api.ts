import type {
  AttendanceOut,
  DecisionIn,
  LateCheckoutOut,
  LeaveOut,
  ScheduleOut,
  SummaryOut,
} from "./types";

const TOKEN_KEY = "attendance_admin_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

type Opts = { method?: string; body?: unknown };

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export async function api<T>(path: string, opts: Opts = {}): Promise<T> {
  const headers = authHeaders();
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(`/api/v1${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : "خطای نامشخص از سرور";
    if (res.status === 401) tokenStore.clear();
    throw new ApiError(res.status, message);
  }
  return data as T;
}

/** دریافت فایل دودویی (مثل خروجی اکسل) با هدر Authorization */
export async function apiBlob(path: string): Promise<Blob> {
  const res = await fetch(`/api/v1${path}`, { headers: authHeaders() });
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : "خطا در دریافت فایل";
    if (res.status === 401) tokenStore.clear();
    throw new ApiError(res.status, message);
  }
  return res.blob();
}

function qs(params: Record<string, string | number | undefined>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== "") p.set(k, String(v));
  }
  return p.toString();
}

/* ---------------- فراخوانی‌های تایپ‌شده پنل مدیر ---------------- */

export const decideLeave = (id: number, body: DecisionIn) =>
  api<LeaveOut>(`/admin/leaves/${id}`, { method: "PATCH", body });

export const decideLateCheckout = (id: number, body: DecisionIn) =>
  api<LateCheckoutOut>(`/admin/late-checkouts/${id}`, { method: "PATCH", body });

export const decideAttendance = (id: number, body: DecisionIn) =>
  api<Pick<AttendanceOut, "id" | "approval_status" | "approval_note">>(
    `/admin/attendance/${id}/decision`,
    { method: "PATCH", body },
  );

export const getSchedule = () => api<ScheduleOut>("/admin/schedule");

export const updateSchedule = (body: {
  work_days: number[];
  start_time: string;
  end_time: string;
  late_grace_minutes: number;
}) => api<ScheduleOut>("/admin/schedule", { method: "PATCH", body });

export const getSummary = (params: { user_id?: string; from_date: string; to_date: string }) =>
  api<SummaryOut>(`/admin/summary?${qs(params)}`);

/** دانلود خروجی اکسل (همه کارمندان اگر user_id داده نشود) */
export const downloadExcel = (params: { user_id?: string; from_date: string; to_date: string }) =>
  apiBlob(`/admin/export/excel?${qs(params)}`);

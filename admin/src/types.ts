export interface Me {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "employee";
  is_active: boolean;
  must_change_password: boolean;
  branch_ids: number[];
}

export interface Employee {
  id: number;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  branch_ids: number[];
}

export interface Branch {
  id: number;
  name: string;
  address: string | null;
  latitude: number;
  longitude: number;
  radius_m: number;
  is_active: boolean;
}

/** وضعیت تایید مدیر روی یک رکورد روزانه */
export type ApprovalStatus = "none" | "approved" | "rejected";

/** وضعیت روز در گزارش‌ها و هفته جاری (قرارداد §۲) */
export type DayStatus =
  | "present"
  | "working"
  | "absent"
  | "incomplete"
  | "rejected"
  | "leave"
  | "pending_checkout"
  | "non_working"
  | "future";

export type LateCheckoutStatus = "pending" | "approved" | "rejected" | "expired";

export type LeaveStatus = "pending" | "approved" | "rejected";

/** بدنه مشترک تصمیم مدیر (مرخصی، خروج فراموش‌شده، حضور و غیاب) */
export interface DecisionIn {
  decision: "approve" | "reject";
  note?: string;
}

export interface AttendanceRow {
  id: number;
  user_id: number;
  user_full_name: string;
  work_date: string;
  branch_id: number;
  branch_name: string;
  check_in_at: string;
  check_out_at: string | null;
  edited_by_admin: boolean;
  work_description: string | null;
  check_out_source: "employee" | "late" | "admin" | null;
  approval_status: ApprovalStatus;
  approval_note: string | null;
  hours_worked: number | null;
  late_minutes: number;
  overtime_minutes: number;
  hourly_leave_hours: number;
  check_in_edited: boolean;
  check_out_edited: boolean;
}

/** خروجی سرور برای هر رکورد حضور و غیاب */
export type AttendanceOut = AttendanceRow;

export interface Dashboard {
  date: string;
  active_employees: number;
  present_today: number;
  absent_today: number;
  leave_today: number;
  rejected_today: number;
  open_check_ins: number;
  pending_leaves: number;
  pending_late_checkouts: number;
  pending_hourly_leaves: number;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
}

export interface LeaveOut {
  id: number;
  user_id: number;
  user_full_name: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: LeaveStatus;
  created_at: string;
  decided_at: string | null;
  decision_note: string | null;
}

export interface HourlyLeaveOut {
  id: number;
  user_id: number;
  user_full_name: string;
  date: string;
  start_hour: number;
  end_hour: number;
  reason: string;
  status: LeaveStatus;
  created_at: string;
  decided_at: string | null;
  decided_by: number | null;
  decision_note: string | null;
}

export interface LateCheckoutOut {
  id: number;
  user_id: number;
  user_full_name: string;
  work_date: string;
  record_id: number;
  requested_at: string;
  check_out_at: string;
  description: string | null;
  status: LateCheckoutStatus;
  branch_name: string | null;
  distance_m: number | null;
  decided_at: string | null;
  decision_note: string | null;
  submission_deadline: string;
  decision_deadline: string;
}

export interface ScheduleOut {
  work_days: number[];
  start_time: string;
  end_time: string;
  late_grace_minutes: number;
  updated_at: string | null;
}

export interface DayStateOut {
  date: string;
  is_work_day: boolean;
  status: DayStatus;
  check_in_at: string | null;
  check_out_at: string | null;
  hours_worked: number | null;
  branch_name: string | null;
  work_description: string | null;
  approval_status: ApprovalStatus;
  approval_note: string | null;
  late_request_status: "pending" | "approved" | "rejected" | "expired" | null;
  pending_leave: boolean;
  is_late: boolean;
  left_early: boolean;
  hourly_leave_hours: number;
  late_minutes: number;
  overtime_minutes: number;
  absence_reason: string | null;
}

export interface WeekOut {
  start: string;
  end: string;
  days: DayStateOut[];
  schedule: ScheduleOut;
}

export interface SummaryTotals {
  present: number;
  absent: number;
  leave: number;
  pending_checkout: number;
  non_working: number;
  future: number;
  total_hours: number;
  late_count: number;
  early_leave_count: number;
  late_minutes: number;
  overtime_minutes: number;
}

export interface SummaryOut {
  user_id: number;
  user_full_name: string;
  from_date: string;
  to_date: string;
  days: DayStateOut[];
  totals: SummaryTotals;
}

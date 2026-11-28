export interface Me {
  id: number;
  username: string;
  full_name: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  branch_ids: number[];
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
}

export type ApprovalStatus = "none" | "approved" | "rejected";
export type CheckOutSource = "employee" | "late" | "admin" | null;

/** Payload shared by every location-aware endpoint. */
export interface LocationIn {
  latitude: number;
  longitude: number;
  accuracy_m: number;
}

/** POST /attendance/check-out */
export interface CheckoutIn extends LocationIn {
  work_description: string;
}

/** POST /attendance/late-checkout */
export interface LateCheckoutIn extends LocationIn {
  work_date: string;
  check_out_time: string;
  description: string;
}

export interface AttendanceOut {
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
  check_out_source: CheckOutSource;
  approval_status: ApprovalStatus;
  approval_note: string | null;
  hours_worked: number | null;
}

/** @deprecated kept for older imports; same shape as AttendanceOut. */
export type AttendanceRow = AttendanceOut;

export interface TodayOut {
  status: "not_checked_in" | "checked_in" | "checked_out";
  record: AttendanceOut | null;
}

/** GET /attendance/week */
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
}

export interface ScheduleOut {
  work_days: number[];
  start_time: string;
  end_time: string;
  late_grace_minutes: number;
  updated_at: string | null;
}

export interface WeekOut {
  start: string;
  end: string;
  days: DayStateOut[];
  schedule: ScheduleOut;
}

/** POST /leaves */
export interface LeaveIn {
  start_date: string;
  end_date: string;
  reason: string;
}

export type RequestStatus = "pending" | "approved" | "rejected";
export type LateCheckoutStatus = RequestStatus | "expired";

export interface HourlyLeaveOut {
  id: number;
  user_id: number;
  user_full_name: string;
  date: string;
  start_hour: number;
  end_hour: number;
  reason: string;
  status: RequestStatus;
  created_at: string;
  decided_at: string | null;
  decided_by: number | null;
  decision_note: string | null;
}

export interface LeaveOut {
  id: number;
  user_id: number;
  user_full_name: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: RequestStatus;
  created_at: string;
  decided_at: string | null;
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
  description: string;
  status: LateCheckoutStatus;
  branch_name: string;
  distance_m: number;
  decided_at: string | null;
  decision_note: string | null;
  submission_deadline: string;
  decision_deadline: string;
}

/** PATCH /admin/leaves/{id}, /admin/late-checkouts/{id}, /admin/attendance/{id}/decision */
export interface DecisionIn {
  decision: "approve" | "reject";
  note?: string | null;
}

/** GET /admin/dashboard */
export interface AdminDashboardOut {
  date: string;
  active_employees: number;
  present_today: number;
  absent_today: number;
  leave_today: number;
  rejected_today: number;
  open_check_ins: number;
  pending_leaves: number;
  pending_late_checkouts: number;
}

/** PATCH /admin/attendance/{id}/decision */
export interface AttendanceDecisionOut {
  id: number;
  approval_status: ApprovalStatus;
  approval_note: string | null;
}

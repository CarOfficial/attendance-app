import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { Alert } from "./components/ui";
import { ChangePasswordPage } from "./pages/ChangePassword";
import { LoginPage } from "./pages/Login";
import { DashboardPage } from "./pages/Dashboard";
import { AttendancePage } from "./pages/Attendance";
import { EmployeesPage } from "./pages/Employees";
import { BranchesPage } from "./pages/Branches";
import { LeavesPage } from "./pages/Leaves";
import { LateCheckoutsPage } from "./pages/LateCheckouts";
import { SchedulePage } from "./pages/Schedule";
import { ReportsPage } from "./pages/Reports";

function Protected() {
  const { me, loading, logout } = useAuth();
  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">در حال بارگذاری…</div>;
  }
  if (!me) return <Navigate to="/login" replace />;
  if (me.must_change_password) return <ChangePasswordPage />;
  if (me.role !== "admin") {
    return (
      <div className="mx-auto mt-24 max-w-md space-y-4 p-4">
        <Alert>این پنل فقط برای مدیران است.</Alert>
        <button onClick={logout} className="text-sm text-indigo-600 hover:underline">خروج</button>
      </div>
    );
  }
  return <Layout />;
}

function LoginGate() {
  const { me, loading } = useAuth();
  if (loading) return null;
  // Any signed-in user goes to the protected area; it decides whether a password change comes first.
  if (me) return <Navigate to="/" replace />;
  return <LoginPage />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginGate />} />
        <Route element={<Protected />}>
          <Route index element={<DashboardPage />} />
          <Route path="attendance" element={<AttendancePage />} />
          <Route path="leaves" element={<LeavesPage />} />
          <Route path="late-checkouts" element={<LateCheckoutsPage />} />
          <Route path="schedule" element={<SchedulePage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="employees" element={<EmployeesPage />} />
          <Route path="branches" element={<BranchesPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

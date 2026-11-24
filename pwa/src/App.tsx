import { BrowserRouter, Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { ChangePasswordPage } from "./pages/ChangePassword";
import { LoginPage } from "./pages/Login";
import { HomePage } from "./pages/Home";
import { WeekPage } from "./pages/Week";
import { RequestsPage } from "./pages/Requests";
import { AdminPage } from "./pages/Admin";
import { HistoryPage } from "./pages/History";

const TABS = [
  { to: "/", label: "ثبت حضور", icon: "◷", end: true },
  { to: "/week", label: "هفته کاری", icon: "▦", end: false },
  { to: "/requests", label: "درخواست‌ها", icon: "✎", end: false },
];

function Shell() {
  const { logout, me } = useAuth();
  const tabs = me?.role === "admin" ? [...TABS, { to: "/admin", label: "مدیریت", icon: "⚙", end: false }] : TABS;
  const tab = "flex flex-1 flex-col items-center gap-1 rounded-2xl py-2 text-[10px] font-medium transition";

  return (
    <div className="aurora flex min-h-dvh flex-col">
      <header className="glass-strong sticky top-0 z-10 mx-3 mt-3 flex items-center justify-between rounded-2xl px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="btn-gold flex h-8 w-8 items-center justify-center rounded-xl text-sm font-bold">ح</div>
          <div className="leading-tight">
            <span className="block text-sm font-bold text-indigo-950">حضور و غیاب</span>
            <span className="block text-[10px] text-indigo-900/55">{me?.full_name}</span>
          </div>
        </div>
        <button onClick={logout} className="rounded-full bg-white/60 px-3 py-1.5 text-xs font-medium text-indigo-800 ring-1 ring-indigo-200">
          خروج
        </button>
      </header>

      <main className="flex-1 px-4 py-6 pb-32">
        <div className="mx-auto max-w-md">
          <Outlet />
        </div>
      </main>

      <nav className="fixed inset-x-3 bottom-[max(0.75rem,env(safe-area-inset-bottom))] z-10 mx-auto max-w-md">
        <div className="glass-strong flex gap-1.5 rounded-[1.75rem] p-1.5">
          {tabs.map((t) => (
            <NavLink
              key={t.to}
              to={t.to}
              end={t.end}
              className={({ isActive }) => `${tab} ${isActive ? "btn-royal" : "text-indigo-900/60"}`}
            >
              <span className="text-lg leading-none">{t.icon}</span>
              {t.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

function Protected() {
  const { me, loading } = useAuth();
  if (loading) {
    return (
      <div className="aurora flex min-h-dvh items-center justify-center">
        <div className="glass rounded-2xl px-6 py-4 text-sm text-indigo-900/70">در حال بارگذاری…</div>
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace />;
  if (me.must_change_password) return <ChangePasswordPage />;
  return <Shell />;
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
          <Route index element={<HomePage />} />
          <Route path="week" element={<WeekPage />} />
          <Route path="requests" element={<RequestsPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="admin" element={<AdminPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

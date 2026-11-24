import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { BrandLogo } from "./ui";

const nav = [
  { to: "/", label: "داشبورد", icon: "◐" },
  { to: "/attendance", label: "حضور و غیاب", icon: "◷" },
  { to: "/leaves", label: "مرخصی‌ها", icon: "☾" },
  { to: "/late-checkouts", label: "خروج فراموش‌شده", icon: "⇦" },
  { to: "/schedule", label: "برنامه کاری", icon: "▦" },
  { to: "/reports", label: "گزارش و ساعات کاری", icon: "▤" },
  { to: "/employees", label: "کارمندان", icon: "◉" },
  { to: "/branches", label: "دفاتر و موقعیت", icon: "◎" },
];

export function Layout() {
  const { me, logout } = useAuth();
  return (
    <div className="aurora min-h-dvh md:flex">
      <aside className="glass-strong z-20 m-3 rounded-3xl md:fixed md:inset-y-3 md:right-3 md:flex md:w-64 md:flex-col md:overflow-hidden">
        <div className="flex items-center gap-3 px-6 py-5">
          <BrandLogo className="h-11 w-11 rounded-2xl" letterClass="text-lg" />
          <div>
            <p className="text-base font-bold text-indigo-950">حضوریار</p>
            <p className="text-xs text-indigo-700/70">همراه هوشمند حضور و غیاب</p>
          </div>
        </div>

        <nav className="scroll-thin flex gap-2 overflow-x-auto px-4 pb-4 md:flex-col md:overflow-visible">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 whitespace-nowrap rounded-2xl px-4 py-3 text-sm font-medium transition ${
                  isActive
                    ? "btn-royal"
                    : "text-indigo-900/70 hover:bg-white/70 hover:text-indigo-900"
                }`
              }
            >
              <span className="text-base opacity-80">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto hidden border-t border-white/70 p-5 md:block">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-purple-500 to-indigo-900 text-sm font-semibold text-white">
              {me?.full_name?.charAt(0)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-indigo-950">{me?.full_name}</p>
              <button onClick={logout} className="text-xs text-rose-600 hover:underline">خروج از حساب</button>
            </div>
          </div>
        </div>
      </aside>

      <main className="flex-1 md:mr-72">
        <div className="mx-auto max-w-6xl p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

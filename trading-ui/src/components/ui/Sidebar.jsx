import { NavLink } from "react-router-dom";
import { LayoutDashboard, PlayCircle, FlaskConical, Clock, TrendingUp, BarChart2, Database, Settings } from "lucide-react";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
  { to: "/sessions", label: "Sessions", Icon: Database },
  { to: "/replay", label: "Market Replay", Icon: PlayCircle },
  { to: "/setup", label: "Strategy Builder", Icon: FlaskConical },
  { to: "/backtests", label: "Backtests", Icon: Clock },
  { to: "/analytics", label: "Analytics", Icon: BarChart2 },
  { to: "/settings", label: "Settings", Icon: Settings },
];

export default function Sidebar() {
  return (
    <nav className="h-full flex flex-col z-40 bg-[#0a0a0a] border-r border-white/5 w-[220px]">
      <div className="px-5 py-5 border-b border-white/5">
        <span className="text-sm font-bold tracking-tight text-white">AlgoTradeX</span>
        <span className="text-[10px] text-[#888] block mt-0.5">FXReplay Terminal</span>
      </div>
      <div className="flex-1 py-3">
        {NAV_ITEMS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-3 text-[13px] font-medium transition-all duration-200 border-l-[3px] ` +
              (isActive
                ? "text-white bg-white/5 border-blue-500"
                : "text-[#888] border-transparent hover:text-white hover:bg-white/[0.03]")
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

import { NavLink, useLocation } from "react-router-dom";
import { BarChart2, Clock, LayoutDashboard, TrendingUp, FlaskConical, PlayCircle, Database, Settings } from "lucide-react";

const NAV_ITEMS = [
    { to: "/dashboard", label: "Dashboard", Icon: LayoutDashboard },
    { to: "/replay", label: "Market Replay", Icon: PlayCircle },
    { to: "/setup", label: "Strategy Lab", Icon: FlaskConical },
    { to: "/backtests", label: "Backtests", Icon: Clock },
    { to: "/results", label: "Results", Icon: TrendingUp },
    { to: "/analytics", label: "Analytics", Icon: BarChart2 },
    { to: "/data", label: "Data Explorer", Icon: Database },
    { to: "/settings", label: "Settings", Icon: Settings },
];



export default function AppNav() {
    return (
        <nav
            className="fixed left-0 top-0 h-full flex flex-col z-40"
            style={{ width: "200px", background: "#0a0a0a", borderRight: "1px solid rgba(255,255,255,0.06)" }}
        >
            {/* Logo */}
            <div className="px-5 py-5 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <span className="text-sm font-bold tracking-tight text-white">AlgoTradeX</span>
                <span className="text-[10px] text-textSecondary block mt-0.5">Research Platform</span>
            </div>

            {/* Links */}
            <div className="flex-1 py-3">
                {NAV_ITEMS.map(({ to, label, Icon }) => (
                    <NavLink
                        key={to}
                        to={to}
                        className={({ isActive }) =>
                            `flex items-center gap-3 px-5 py-3 text-[13px] font-medium transition-all duration-200 border-l-[3px] ` +
                            (isActive
                                ? "text-textPrimary bg-white/5 border-white/70"
                                : "text-textSecondary border-transparent hover:text-textPrimary hover:bg-white/[0.03]")
                        }
                    >
                        <Icon size={16} />
                        {label}
                    </NavLink>
                ))}
            </div>

            {/* Footer */}
            <div className="px-5 py-4 border-t" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <span className="text-[10px] text-textSecondary">v2.0.0</span>
            </div>
        </nav>
    );
}

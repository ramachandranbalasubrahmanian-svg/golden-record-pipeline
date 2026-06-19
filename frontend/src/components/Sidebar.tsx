import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, ShieldCheck, Users, MessageSquare,
  GitBranch, UserCircle, Settings, Database,
} from "lucide-react";

const LINKS = [
  { to: "/", label: "Admin Console", icon: LayoutDashboard },
  { to: "/data-quality", label: "Data Quality", icon: Database },
  { to: "/stewardship", label: "Stewardship", icon: ShieldCheck },
  { to: "/golden-records", label: "Golden Records", icon: Users },
  { to: "/compliance-chat", label: "Compliance Query", icon: MessageSquare },
  { to: "/lineage", label: "Lineage", icon: GitBranch },
  { to: "/customer-portal", label: "Customer Portal", icon: UserCircle },
];

export function Sidebar() {
  return (
    <aside className="w-60 min-h-screen bg-slate-900 flex flex-col shrink-0">
      <div className="px-4 py-5 border-b border-slate-700">
        <p className="text-indigo-400 font-bold text-sm uppercase tracking-widest">GR Pipeline</p>
        <p className="text-slate-400 text-xs mt-0.5">Golden Record Suite</p>
      </div>
      <nav className="flex-1 py-4 space-y-0.5">
        {LINKS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-4 py-3 border-t border-slate-700">
        <p className="text-slate-500 text-xs">API: {import.meta.env.VITE_API_URL ?? "localhost:8000"}</p>
      </div>
    </aside>
  );
}

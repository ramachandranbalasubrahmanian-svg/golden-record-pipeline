import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import {
  LayoutDashboard, ShieldCheck, Users, MessageSquare,
  GitBranch, UserCircle, Database, Zap,
} from "lucide-react";

const LINKS = [
  { to: "/",                label: "Admin Console",   icon: LayoutDashboard, dot: "bg-indigo-400",  active: "text-indigo-400" },
  { to: "/data-quality",    label: "Data Quality",    icon: Database,         dot: "bg-blue-400",    active: "text-blue-400" },
  { to: "/stewardship",     label: "Stewardship",     icon: ShieldCheck,      dot: "bg-purple-400",  active: "text-purple-400" },
  { to: "/golden-records",  label: "Golden Records",  icon: Users,            dot: "bg-emerald-400", active: "text-emerald-400" },
  { to: "/compliance-chat", label: "Compliance AI",   icon: MessageSquare,    dot: "bg-cyan-400",    active: "text-cyan-400" },
  { to: "/lineage",         label: "Lineage",         icon: GitBranch,        dot: "bg-amber-400",   active: "text-amber-400" },
  { to: "/customer-portal", label: "Customer Portal", icon: UserCircle,       dot: "bg-pink-400",    active: "text-pink-400" },
];

export function Sidebar() {
  return (
    <motion.aside
      initial={{ x: -80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-60 min-h-screen bg-slate-950 flex flex-col shrink-0 border-r border-slate-800/60"
    >
      <div className="px-5 py-5 border-b border-slate-800/60">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Zap size={15} className="text-white" />
          </div>
          <div>
            <p className="text-white font-bold text-sm">GR Pipeline</p>
            <p className="text-slate-500 text-xs">Golden Record Suite</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {LINKS.map(({ to, label, icon: Icon, dot, active }, i) => (
          <NavLink key={to} to={to} end={to === "/"} className="block">
            {({ isActive }) => (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04, duration: 0.3 }}
                className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-slate-800 text-white shadow-sm"
                    : "text-slate-400 hover:text-white hover:bg-slate-900"
                }`}
              >
                <Icon size={16} className={isActive ? active : undefined} />
                <span>{label}</span>
                {isActive && (
                  <motion.div
                    layoutId="sidebar-dot"
                    className={`ml-auto w-1.5 h-1.5 rounded-full ${dot}`}
                    transition={{ type: "spring", bounce: 0.3, duration: 0.4 }}
                  />
                )}
              </motion.div>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-slate-800/60">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <p className="text-slate-500 text-xs">API live</p>
        </div>
      </div>
    </motion.aside>
  );
}

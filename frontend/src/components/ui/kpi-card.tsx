"use client";
import { motion, animate, useMotionValue } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import { cn } from "src/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  trend?: number;
  icon?: React.ReactNode;
  color?: "indigo" | "green" | "amber" | "red" | "purple";
  delay?: number;
  description?: string;
}

const COLORS = {
  indigo: { bg: "from-indigo-500/10 to-indigo-600/5", border: "border-indigo-200", icon: "bg-indigo-100 text-indigo-600", glow: "shadow-indigo-100" },
  green:  { bg: "from-emerald-500/10 to-emerald-600/5", border: "border-emerald-200", icon: "bg-emerald-100 text-emerald-600", glow: "shadow-emerald-100" },
  amber:  { bg: "from-amber-500/10 to-amber-600/5", border: "border-amber-200", icon: "bg-amber-100 text-amber-600", glow: "shadow-amber-100" },
  red:    { bg: "from-red-500/10 to-red-600/5", border: "border-red-200", icon: "bg-red-100 text-red-600", glow: "shadow-red-100" },
  purple: { bg: "from-purple-500/10 to-purple-600/5", border: "border-purple-200", icon: "bg-purple-100 text-purple-600", glow: "shadow-purple-100" },
};

export function KpiCard({ label, value, suffix = "", prefix = "", decimals = 0, trend, icon, color = "indigo", delay = 0, description }: KpiCardProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const motionVal = useMotionValue(0);
  const { ref, inView } = useInView({ triggerOnce: true });
  const c = COLORS[color];

  useEffect(() => {
    if (!inView) return;
    const controls = animate(motionVal, value, {
      duration: 1.2,
      ease: "easeOut",
      delay,
      onUpdate: (v) => setDisplayValue(decimals > 0 ? parseFloat(v.toFixed(decimals)) : Math.round(v)),
    });
    return controls.stop;
  }, [inView, value, delay, decimals, motionVal]);

  const trendIcon = trend != null
    ? trend > 0 ? <TrendingUp size={12} /> : trend < 0 ? <TrendingDown size={12} /> : <Minus size={12} />
    : null;
  const trendColor = trend != null ? (trend > 0 ? "text-emerald-600" : trend < 0 ? "text-red-500" : "text-slate-400") : "";

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      whileHover={{ y: -2, boxShadow: "0 10px 30px rgba(0,0,0,0.08)" }}
      className={cn(
        "bg-white rounded-2xl border p-5 shadow-sm card-hover cursor-default",
        "bg-gradient-to-br",
        c.bg, c.border
      )}
    >
      <div className="flex items-start justify-between mb-4">
        {icon && (
          <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", c.icon)}>
            {icon}
          </div>
        )}
        {trend != null && (
          <span className={cn("flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded-full", trendColor, "bg-current/10")}>
            {trendIcon}{Math.abs(trend)}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-slate-900 tabular-nums">
        {prefix}{decimals > 0 ? displayValue.toFixed(decimals) : displayValue.toLocaleString()}{suffix}
      </p>
      <p className="text-sm font-medium text-slate-500 mt-1">{label}</p>
      {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
    </motion.div>
  );
}

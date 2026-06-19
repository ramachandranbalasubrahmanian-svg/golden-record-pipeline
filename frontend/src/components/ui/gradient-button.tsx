"use client";
import { motion } from "framer-motion";
import { cn } from "src/lib/utils";

interface GradientButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "indigo" | "green" | "red" | "amber";
  size?: "sm" | "md" | "lg";
}

const VARIANTS = {
  indigo: "from-indigo-500 via-purple-500 to-indigo-600",
  green:  "from-emerald-500 via-green-500 to-teal-600",
  red:    "from-rose-500 via-red-500 to-rose-600",
  amber:  "from-amber-400 via-orange-500 to-amber-600",
};

const SIZES = {
  sm: "px-3 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export function GradientButton({
  children, className, variant = "indigo", size = "md", ...props
}: GradientButtonProps) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.97 }}
      className={cn(
        "relative inline-flex items-center gap-2 rounded-lg font-semibold text-white",
        "bg-gradient-to-r shadow-lg transition-shadow hover:shadow-xl",
        "focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...(props as any)}
    >
      <span className="relative z-10 flex items-center gap-2">{children}</span>
      <span
        className={cn(
          "absolute inset-0 rounded-lg opacity-0 bg-gradient-to-r bg-[length:200%_100%] animate-shimmer transition-opacity hover:opacity-100",
          VARIANTS[variant]
        )}
      />
    </motion.button>
  );
}

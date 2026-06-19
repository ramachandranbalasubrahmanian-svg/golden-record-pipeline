import { clsx } from "clsx";

type Variant = "green" | "amber" | "red" | "blue" | "purple" | "gray" | "orange";

const COLORS: Record<Variant, string> = {
  green: "bg-green-100 text-green-800",
  amber: "bg-amber-100 text-amber-800",
  red: "bg-red-100 text-red-800",
  blue: "bg-blue-100 text-blue-800",
  purple: "bg-purple-100 text-purple-800",
  gray: "bg-slate-100 text-slate-700",
  orange: "bg-orange-100 text-orange-800",
};

export function Badge({ label, variant }: { label: string; variant: Variant }) {
  return (
    <span className={clsx("inline-flex items-center px-2 py-0.5 rounded text-xs font-medium", COLORS[variant])}>
      {label}
    </span>
  );
}

export function riskVariant(r: string): Variant {
  return ({ LOW: "gray", MEDIUM: "amber", HIGH: "orange", CRITICAL: "red" }[r] ?? "gray") as Variant;
}

export function kycVariant(s: string): Variant {
  return ({ VERIFIED: "green", PENDING: "blue", FAILED: "red", EXPIRED: "amber" }[s] ?? "gray") as Variant;
}

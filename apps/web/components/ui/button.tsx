import * as React from "react";

import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => {
  const variantClass =
    variant === "secondary"
      ? "border border-white/10 bg-white/5 text-slate-100 hover:bg-white/8"
      : variant === "ghost"
        ? "text-slate-300 hover:bg-white/6"
        : "bg-[linear-gradient(135deg,#1bb6ff,#00d3c7)] text-slate-950 shadow-[0_12px_30px_rgba(0,180,255,0.2)] hover:scale-[1.01]";
  const sizeClass = size === "sm" ? "h-8 px-3" : size === "lg" ? "h-11 px-5" : "h-10 px-4 py-2";
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-full text-sm font-medium transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:pointer-events-none disabled:opacity-50",
        variantClass,
        sizeClass,
        className,
      )}
      ref={ref}
      {...props}
    />
  );
});
Button.displayName = "Button";

export { Button };

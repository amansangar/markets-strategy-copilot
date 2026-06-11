import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(18,26,39,0.94),rgba(10,16,28,0.98))] shadow-[0_14px_40px_rgba(0,0,0,0.28)] backdrop-blur",
        className,
      )}
      {...props}
    />
  );
}

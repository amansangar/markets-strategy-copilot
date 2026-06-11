"use client";

import { createContext, useContext, useState, type HTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/utils";

const TabsContext = createContext<{ value: string; setValue: (value: string) => void } | null>(null);

export function Tabs({ defaultValue, children }: { defaultValue: string; children: ReactNode }) {
  const [value, setValue] = useState(defaultValue);
  return <TabsContext.Provider value={{ value, setValue }}>{children}</TabsContext.Provider>;
}

export function TabsList({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-wrap gap-2", className)} {...props} />;
}

export function TabsTrigger({ className, value, children }: { className?: string; value: string; children: ReactNode }) {
  const context = useContext(TabsContext);
  if (!context) return null;
  return (
    <button
      type="button"
      onClick={() => context.setValue(value)}
      className={cn(
        "rounded-full border border-white/8 bg-white/4 px-4 py-2 text-sm text-slate-300 transition",
        context.value === value && "border-cyan-300/30 bg-cyan-300/12 text-white",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({ className, value, children }: { className?: string; value: string; children: ReactNode }) {
  const context = useContext(TabsContext);
  if (!context || context.value !== value) {
    return null;
  }
  return <div className={cn("mt-4", className)}>{children}</div>;
}

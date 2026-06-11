import { IconShield } from "@/components/icons";
import { Card } from "@/components/ui/card";

export function LiveFallbackNotice({ message, title = "Live fallback active" }: { message: string; title?: string }) {
  return (
    <Card className="border-amber-300/18 bg-amber-300/8 p-4">
      <div className="flex gap-3">
        <div className="mt-0.5 rounded-2xl border border-amber-300/20 bg-amber-300/10 p-2 text-amber-100">
          <IconShield className="h-4 w-4" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-amber-100">{title}</p>
          <p className="mt-2 text-sm leading-6 text-slate-300">{message}</p>
        </div>
      </div>
    </Card>
  );
}

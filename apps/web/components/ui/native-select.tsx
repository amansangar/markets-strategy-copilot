export function NativeSelect({
  value,
  onChange,
  children,
}: {
  value: string;
  onChange: (value: string) => void;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-10 w-full rounded-full border border-white/10 bg-slate-950 px-4 text-sm text-slate-100 [color-scheme:dark] outline-none ring-cyan-300/20 transition hover:border-cyan-300/25 focus:border-cyan-300/40 focus:ring-4 [&>option]:bg-slate-950 [&>option]:text-slate-100"
    >
      {children}
    </select>
  );
}

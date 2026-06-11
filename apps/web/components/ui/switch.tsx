export function Switch({
  checked,
  onCheckedChange,
  label = "Toggle setting",
}: {
  checked?: boolean;
  onCheckedChange?: (value: boolean) => void;
  label?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onCheckedChange?.(!checked)}
      className="relative z-20 inline-flex h-8 w-14 shrink-0 cursor-pointer rounded-full border border-white/10 bg-white/10 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-200"
    >
      <span
        className="absolute inset-0 rounded-full transition-colors"
        style={{ background: checked ? "rgba(74, 245, 157, 0.5)" : "transparent" }}
      />
      <span
        className="absolute top-1 block h-6 w-6 rounded-full bg-white shadow transition-transform"
        style={{ transform: checked ? "translateX(26px)" : "translateX(4px)" }}
      />
    </button>
  );
}

import type { SVGProps } from "react";

function IconBase({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...props}>
      {children}
    </svg>
  );
}

export function IconChart(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M4 19h16" />
      <path d="M6 16l4-5 3 2 5-7" />
      <path d="M18 6h-4v4" />
    </IconBase>
  );
}

export function IconBell(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M6 10a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6" />
      <path d="M10 20a2 2 0 0 0 4 0" />
    </IconBase>
  );
}

export function IconTrendUp(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M4 16l6-6 4 4 6-8" />
      <path d="M20 6h-5" />
      <path d="M20 6v5" />
    </IconBase>
  );
}

export function IconTrendDown(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M4 8l6 6 4-4 6 8" />
      <path d="M20 18h-5" />
      <path d="M20 18v-5" />
    </IconBase>
  );
}

export function IconGauge(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M5 16a7 7 0 1 1 14 0" />
      <path d="M12 13l3-3" />
      <path d="M12 18h.01" />
    </IconBase>
  );
}

export function IconSignal(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M4 18h2" />
      <path d="M8 14h2" />
      <path d="M12 10h2" />
      <path d="M16 6h4" />
    </IconBase>
  );
}

export function IconWarning(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M12 3l9 16H3z" />
      <path d="M12 9v4" />
      <path d="M12 17h.01" />
    </IconBase>
  );
}

export function IconShield(props: SVGProps<SVGSVGElement>) {
  return (
    <IconBase {...props}>
      <path d="M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6z" />
    </IconBase>
  );
}

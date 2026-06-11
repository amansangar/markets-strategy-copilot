export function formatPrice(value: number) {
  if (Math.abs(value) >= 1000) {
    return new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 }).format(value);
  }
  return new Intl.NumberFormat("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 4 }).format(value);
}

export function formatPercent(value: number) {
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

export function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function formatDate(value: string | number | Date) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function formatDateTime(value: string | number | Date) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(new Date(value));
}

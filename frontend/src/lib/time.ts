/** DB timestamps are UTC-naive (SQLite CURRENT_TIMESTAMP / utcnow()).
 * Browsers parse "2026-09-04T11:00:00" as LOCAL time, which silently shifts
 * the trail by hours. Treat stored values as UTC and always render IST —
 * this console prices in rupees for Indian merchants, so IST is the wall
 * clock that matters, regardless of viewer timezone. */

function asUtc(timestamp: string): Date {
  const hasOffset = /([zZ]|[+-]\d{2}:?\d{2})$/.test(timestamp.trim());
  return new Date(hasOffset ? timestamp : `${timestamp.trim()}Z`);
}

export function formatTimeIST(timestamp?: string | null): string {
  if (!timestamp) return "";
  const date = asUtc(timestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatDateTimeIST(timestamp?: string | null): string {
  if (!timestamp) return "—";
  const date = asUtc(timestamp);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

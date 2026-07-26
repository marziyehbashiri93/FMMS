/** ISO `yyyy-MM-dd` ranges compare lexicographically. */
export function isValidIsoDateRange(fromDate?: string, toDate?: string): boolean {
  if (!fromDate || !toDate) return true;
  return fromDate <= toDate;
}

export const DATE_RANGE_ORDER_ERROR = 'از تاریخ نباید بعد از تا تاریخ باشد';

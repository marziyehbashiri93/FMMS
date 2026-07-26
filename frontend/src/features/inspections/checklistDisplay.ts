import type { Inspection } from '../../types/fmms';

/** Failures first so defect details surface before passing items. */
export function sortChecklistItems(
  items: Inspection['items'] | null | undefined,
): Inspection['items'] {
  if (!items?.length) return [];
  return [...items].sort((a, b) => {
    const aRank = a.result === 'FAIL' ? 0 : a.result === 'PASS' ? 2 : 1;
    const bRank = b.result === 'FAIL' ? 0 : b.result === 'PASS' ? 2 : 1;
    return aRank - bRank;
  });
}

export function checklistOverallTone(
  hasFailures: boolean,
  overallResult?: string | null,
): 'error' | 'success' {
  if (hasFailures || overallResult === 'FAIL') return 'error';
  return 'success';
}

export function checklistOverallLabel(
  hasFailures: boolean,
  overallResult: string | null | undefined,
  resultLabels: Record<string, string>,
): string {
  if (hasFailures) return 'دارای خرابی';
  return resultLabels[overallResult ?? ''] ?? overallResult ?? '—';
}

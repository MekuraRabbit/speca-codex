import type { Severity } from '@/types/pipeline';

const SEVERITY_ORDER: Record<string, number> = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
  Informational: 4,
};

export function severityRank(severity: string): number {
  return SEVERITY_ORDER[severity] ?? 5;
}

export function compareSeverity(a: string, b: string): number {
  return severityRank(a) - severityRank(b);
}

export function severityColor(severity: string): string {
  switch (severity) {
    case 'Critical': return 'var(--color-critical)';
    case 'High': return 'var(--color-high)';
    case 'Medium': return 'var(--color-medium)';
    case 'Low': return 'var(--color-low)';
    case 'Informational': return 'var(--color-informational)';
    default: return 'var(--color-text-muted)';
  }
}

export function severityBgColor(severity: string): string {
  switch (severity) {
    case 'Critical': return 'var(--color-critical-bg)';
    case 'High': return 'var(--color-high-bg)';
    case 'Medium': return 'var(--color-medium-bg)';
    case 'Low': return 'var(--color-low-bg)';
    case 'Informational': return 'var(--color-informational-bg)';
    default: return 'var(--color-surface-alt)';
  }
}

export const SEVERITIES: Severity[] = ['Critical', 'High', 'Medium', 'Low', 'Informational'];

export function countBySeverity(items: Array<{ severity?: string }>): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const s of SEVERITIES) counts[s] = 0;
  for (const item of items) {
    const sev = item.severity ?? 'Informational';
    counts[sev] = (counts[sev] ?? 0) + 1;
  }
  return counts;
}

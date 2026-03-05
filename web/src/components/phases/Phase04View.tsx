import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { DataTable, type Column } from '@/components/common/DataTable';
import { FilterBar } from '@/components/common/FilterBar';
import { SeverityBadge } from '@/components/common/SeverityBadge';
import { truncate } from '@/lib/format';
import type { Phase04Data, ReviewedItem } from '@/types/pipeline';

const VERDICT_OPTIONS = [
  { value: 'CONFIRMED_VULNERABILITY', label: ja.verdict_confirmed_vulnerability },
  { value: 'CONFIRMED_POTENTIAL', label: ja.verdict_confirmed_potential },
  { value: 'DISPUTED_FP', label: ja.verdict_disputed_fp },
  { value: 'DOWNGRADED', label: ja.verdict_downgraded },
  { value: 'NEEDS_MANUAL_REVIEW', label: ja.verdict_needs_manual_review },
  { value: 'PASS_THROUGH', label: ja.verdict_pass_through },
];

function verdictLabel(v: string): string {
  const opt = VERDICT_OPTIONS.find((o) => o.value === v);
  return opt?.label ?? v;
}

function verdictColor(v: string): string {
  switch (v) {
    case 'CONFIRMED_VULNERABILITY':
    case 'CONFIRMED_POTENTIAL':
      return 'var(--color-confirmed)';
    case 'DISPUTED_FP':
      return 'var(--color-disputed)';
    case 'NEEDS_MANUAL_REVIEW':
      return 'var(--color-needs-review)';
    default:
      return 'var(--color-pass-through)';
  }
}

const columns: Column<ReviewedItem>[] = [
  {
    key: 'property_id',
    label: ja.col_property_id,
    render: (item) => <code>{item.property_id}</code>,
    sortable: true,
    sortValue: (item) => item.property_id,
    width: '160px',
  },
  {
    key: 'verdict',
    label: ja.col_verdict,
    render: (item) => (
      <span style={{ color: verdictColor(item.review_verdict), fontWeight: 600 }}>
        {verdictLabel(item.review_verdict)}
      </span>
    ),
    sortable: true,
    sortValue: (item) => item.review_verdict,
    width: '160px',
  },
  {
    key: 'adjusted_severity',
    label: ja.col_adjusted_severity,
    render: (item) => item.adjusted_severity ? <SeverityBadge severity={item.adjusted_severity} /> : '-',
    sortable: true,
    sortValue: (item) => item.adjusted_severity ?? '',
    width: '120px',
  },
  {
    key: 'reviewer_notes',
    label: ja.col_reviewer_notes,
    render: (item) => truncate(item.reviewer_notes ?? '', 100),
  },
  {
    key: 'recommendation',
    label: ja.col_recommendation,
    render: (item) => truncate(item.final_recommendation ?? '', 80),
  },
];

interface Props {
  data: Phase04Data;
}

export function Phase04View({ data }: Props) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Record<string, string>>({});

  const filtered = useMemo(() => {
    let items = data.reviewed_items;
    if (filters.verdict) {
      items = items.filter((p) => p.review_verdict === filters.verdict);
    }
    return items;
  }, [data.reviewed_items, filters]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      <FilterBar
        filters={[
          {
            key: 'verdict',
            label: ja.filter_verdict,
            options: VERDICT_OPTIONS,
          },
        ]}
        values={filters}
        onChange={(k, v) => setFilters((f) => ({ ...f, [k]: v }))}
      />
      <DataTable
        data={filtered as (ReviewedItem & Record<string, unknown>)[]}
        columns={columns as Column<ReviewedItem & Record<string, unknown>>[]}
        keyField="property_id"
        searchFields={(item) =>
          `${item.property_id} ${item.reviewer_notes ?? ''} ${item.final_recommendation ?? ''}`
        }
        onRowClick={(item) => navigate(`/property/${item.property_id}`)}
      />
    </div>
  );
}

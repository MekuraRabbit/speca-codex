import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { DataTable, type Column } from '@/components/common/DataTable';
import { FilterBar } from '@/components/common/FilterBar';
import { truncate } from '@/lib/format';
import type { Phase03Data, AuditMapItem } from '@/types/pipeline';

const CLASSIFICATION_OPTIONS = [
  { value: 'vulnerable', label: ja.classification_vulnerable },
  { value: 'safe', label: ja.classification_safe },
  { value: 'inconclusive', label: ja.classification_inconclusive },
  { value: 'potential-vulnerability', label: ja.classification_potential },
  { value: 'out-of-scope', label: ja.classification_out_of_scope },
  { value: 'informational', label: ja.classification_informational },
];

function classificationLabel(cls: string): string {
  const opt = CLASSIFICATION_OPTIONS.find((o) => o.value === cls);
  return opt?.label ?? cls;
}

const columns: Column<AuditMapItem>[] = [
  {
    key: 'property_id',
    label: ja.col_property_id,
    render: (item) => <code>{item.property_id}</code>,
    sortable: true,
    sortValue: (item) => item.property_id,
    width: '160px',
  },
  {
    key: 'classification',
    label: ja.col_classification,
    render: (item) => classificationLabel(item.classification),
    sortable: true,
    sortValue: (item) => item.classification,
    width: '140px',
  },
  {
    key: 'summary',
    label: ja.col_summary,
    render: (item) => truncate(item.summary ?? '', 100),
  },
  {
    key: 'attack_scenario',
    label: ja.col_attack_scenario,
    render: (item) => truncate(item.attack_scenario ?? '', 80),
  },
  {
    key: 'bug_bounty',
    label: ja.col_bug_bounty,
    render: (item) =>
      item.bug_bounty_eligible === true
        ? ja.yes
        : item.bug_bounty_eligible === false
          ? ja.no
          : '-',
    width: '80px',
  },
];

interface Props {
  data: Phase03Data;
}

export function Phase03View({ data }: Props) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Record<string, string>>({});

  const filtered = useMemo(() => {
    let items = data.audit_items;
    if (filters.classification) {
      items = items.filter((p) => p.classification === filters.classification);
    }
    return items;
  }, [data.audit_items, filters]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      <FilterBar
        filters={[
          {
            key: 'classification',
            label: ja.filter_classification,
            options: CLASSIFICATION_OPTIONS,
          },
        ]}
        values={filters}
        onChange={(k, v) => setFilters((f) => ({ ...f, [k]: v }))}
      />
      <DataTable
        data={filtered as (AuditMapItem & Record<string, unknown>)[]}
        columns={columns as Column<AuditMapItem & Record<string, unknown>>[]}
        keyField="property_id"
        searchFields={(item) =>
          `${item.property_id} ${item.summary ?? ''} ${item.attack_scenario ?? ''}`
        }
        onRowClick={(item) => navigate(`/property/${item.property_id}`)}
      />
    </div>
  );
}

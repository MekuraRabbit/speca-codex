import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { DataTable, type Column } from '@/components/common/DataTable';
import { FilterBar } from '@/components/common/FilterBar';
import { SeverityBadge } from '@/components/common/SeverityBadge';
import { SEVERITIES } from '@/lib/severity';
import { truncate } from '@/lib/format';
import type { Phase01eData, Property } from '@/types/pipeline';

const columns: Column<Property>[] = [
  {
    key: 'property_id',
    label: ja.col_property_id,
    render: (item) => <code>{item.property_id}</code>,
    sortable: true,
    sortValue: (item) => item.property_id,
    width: '160px',
  },
  {
    key: 'severity',
    label: ja.col_severity,
    render: (item) => <SeverityBadge severity={item.severity} />,
    sortable: true,
    sortValue: (item) => item.severity,
    width: '100px',
  },
  {
    key: 'type',
    label: ja.col_type,
    render: (item) => item.type,
    sortable: true,
    sortValue: (item) => item.type,
    width: '120px',
  },
  {
    key: 'text',
    label: ja.col_text,
    render: (item) => truncate(item.text, 100),
  },
  {
    key: 'covers',
    label: ja.col_covers,
    render: (item) => <code>{item.covers}</code>,
    width: '100px',
  },
  {
    key: 'bug_bounty_eligible',
    label: ja.col_bug_bounty,
    render: (item) => item.bug_bounty_eligible ? ja.yes : ja.no,
    width: '80px',
  },
];

interface Props {
  data: Phase01eData;
}

export function Phase01eView({ data }: Props) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Record<string, string>>({});

  const filtered = useMemo(() => {
    let items = data.properties;
    if (filters.severity) {
      items = items.filter((p) => p.severity === filters.severity);
    }
    if (filters.type) {
      items = items.filter((p) => p.type === filters.type);
    }
    return items;
  }, [data.properties, filters]);

  const types = useMemo(() => {
    const set = new Set(data.properties.map((p) => p.type));
    return [...set].sort();
  }, [data.properties]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      <FilterBar
        filters={[
          {
            key: 'severity',
            label: ja.filter_severity,
            options: SEVERITIES.map((s) => ({ value: s, label: s })),
          },
          {
            key: 'type',
            label: ja.filter_type,
            options: types.map((t) => ({ value: t, label: t })),
          },
        ]}
        values={filters}
        onChange={(k, v) => setFilters((f) => ({ ...f, [k]: v }))}
      />
      <DataTable
        data={filtered as (Property & Record<string, unknown>)[]}
        columns={columns as Column<Property & Record<string, unknown>>[]}
        keyField="property_id"
        searchFields={(item) =>
          `${item.property_id} ${item.text} ${item.assertion} ${item.covers}`
        }
        onRowClick={(item) => navigate(`/property/${item.property_id}`)}
      />
    </div>
  );
}

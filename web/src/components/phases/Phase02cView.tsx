import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import { DataTable, type Column } from '@/components/common/DataTable';
import { FilterBar } from '@/components/common/FilterBar';
import { SeverityBadge } from '@/components/common/SeverityBadge';
import { SEVERITIES } from '@/lib/severity';
import { truncate } from '@/lib/format';
import type { Phase02cData, PropertyWithCode } from '@/types/pipeline';

const RESOLUTION_OPTIONS = [
  { value: 'resolved', label: ja.resolution_resolved },
  { value: 'not_found', label: ja.resolution_not_found },
  { value: 'specification_only', label: ja.resolution_specification_only },
  { value: 'out_of_scope', label: ja.resolution_out_of_scope },
  { value: 'skipped', label: ja.resolution_skipped },
  { value: 'error', label: ja.resolution_error },
];

const columns: Column<PropertyWithCode>[] = [
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
    key: 'text',
    label: ja.col_text,
    render: (item) => truncate(item.text, 80),
  },
  {
    key: 'resolution',
    label: ja.col_resolution,
    render: (item) => item.code_scope?.resolution_status ?? '-',
    sortable: true,
    sortValue: (item) => item.code_scope?.resolution_status ?? '',
    width: '120px',
  },
  {
    key: 'file',
    label: ja.col_file,
    render: (item) => {
      const loc = item.code_scope?.locations?.[0];
      return loc ? <code>{truncate(loc.file, 50)}</code> : '-';
    },
  },
];

interface Props {
  data: Phase02cData;
}

export function Phase02cView({ data }: Props) {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Record<string, string>>({});

  const filtered = useMemo(() => {
    let items = data.properties_with_code;
    if (filters.severity) {
      items = items.filter((p) => p.severity === filters.severity);
    }
    if (filters.resolution) {
      items = items.filter(
        (p) => p.code_scope?.resolution_status === filters.resolution,
      );
    }
    return items;
  }, [data.properties_with_code, filters]);

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
            key: 'resolution',
            label: ja.filter_resolution,
            options: RESOLUTION_OPTIONS,
          },
        ]}
        values={filters}
        onChange={(k, v) => setFilters((f) => ({ ...f, [k]: v }))}
      />
      <DataTable
        data={filtered as (PropertyWithCode & Record<string, unknown>)[]}
        columns={columns as Column<PropertyWithCode & Record<string, unknown>>[]}
        keyField="property_id"
        searchFields={(item) =>
          `${item.property_id} ${item.text} ${item.code_scope?.locations?.map((l) => l.file).join(' ') ?? ''}`
        }
        onRowClick={(item) => navigate(`/property/${item.property_id}`)}
      />
    </div>
  );
}

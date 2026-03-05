import { ja } from '@/i18n/ja';
import { DataTable, type Column } from '@/components/common/DataTable';
import type { Phase01aData, DiscoveredSpec } from '@/types/pipeline';
import { truncate } from '@/lib/format';

const columns: Column<DiscoveredSpec>[] = [
  {
    key: 'title',
    label: ja.col_title,
    render: (item) => truncate(item.title, 80),
    sortable: true,
    sortValue: (item) => item.title,
  },
  {
    key: 'url',
    label: ja.col_url,
    render: (item) => (
      <a href={item.url} target="_blank" rel="noopener noreferrer" className="mono">
        {truncate(item.url, 60)}
      </a>
    ),
    sortable: true,
    sortValue: (item) => item.url,
  },
  {
    key: 'status',
    label: ja.col_status,
    render: (item) => item.status,
    sortable: true,
    sortValue: (item) => item.status,
    width: '100px',
  },
];

interface Props {
  data: Phase01aData;
}

export function Phase01aView({ data }: Props) {
  return (
    <DataTable
      data={data.found_specs as (DiscoveredSpec & Record<string, unknown>)[]}
      columns={columns as Column<DiscoveredSpec & Record<string, unknown>>[]}
      keyField="url"
      searchFields={(item) => `${item.title} ${item.url}`}
    />
  );
}

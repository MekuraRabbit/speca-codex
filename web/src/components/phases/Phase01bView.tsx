import { ja } from '@/i18n/ja';
import { DataTable, type Column } from '@/components/common/DataTable';
import type { Phase01bData, SpecSubGraphs } from '@/types/pipeline';
import { truncate } from '@/lib/format';

const columns: Column<SpecSubGraphs>[] = [
  {
    key: 'title',
    label: ja.col_title,
    render: (item) => truncate(item.title, 80),
    sortable: true,
    sortValue: (item) => item.title,
  },
  {
    key: 'source_url',
    label: ja.col_source_url,
    render: (item) => (
      <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="mono">
        {truncate(item.source_url, 50)}
      </a>
    ),
    sortable: true,
    sortValue: (item) => item.source_url,
  },
  {
    key: 'sub_graph_count',
    label: ja.col_subgraph_count,
    render: (item) => item.sub_graphs.length,
    sortable: true,
    sortValue: (item) => item.sub_graphs.length,
    width: '120px',
  },
];

interface Props {
  data: Phase01bData;
}

export function Phase01bView({ data }: Props) {
  return (
    <DataTable
      data={data.specs as (SpecSubGraphs & Record<string, unknown>)[]}
      columns={columns as Column<SpecSubGraphs & Record<string, unknown>>[]}
      keyField="source_url"
      searchFields={(item) => `${item.title} ${item.source_url}`}
    />
  );
}

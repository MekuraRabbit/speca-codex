import { useState, useMemo } from 'react';
import { ja } from '@/i18n/ja';
import styles from './DataTable.module.css';

export interface Column<T> {
  key: string;
  label: string;
  render: (item: T) => React.ReactNode;
  sortable?: boolean;
  sortValue?: (item: T) => string | number;
  width?: string;
}

interface Props<T> {
  data: T[];
  columns: Column<T>[];
  keyField: string;
  onRowClick?: (item: T) => void;
  searchFields?: (item: T) => string;
  emptyMessage?: string;
}

export function DataTable<T extends Record<string, unknown>>({
  data,
  columns,
  keyField,
  onRowClick,
  searchFields,
  emptyMessage,
}: Props<T>) {
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const filtered = useMemo(() => {
    if (!search || !searchFields) return data;
    const q = search.toLowerCase();
    return data.filter((item) => searchFields(item).toLowerCase().includes(q));
  }, [data, search, searchFields]);

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sortValue) return filtered;
    const getValue = col.sortValue;
    return [...filtered].sort((a, b) => {
      const va = getValue(a);
      const vb = getValue(b);
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [filtered, sortKey, sortDir, columns]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <div className={styles.wrapper}>
      {searchFields && (
        <div className={styles.searchBar}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={ja.search_placeholder}
            className={styles.searchInput}
          />
          <span className={styles.count}>
            {sorted.length}{ja.items_count}
          </span>
        </div>
      )}
      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  style={col.width ? { width: col.width } : undefined}
                  className={col.sortable ? styles.sortable : undefined}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                >
                  {col.label}
                  {sortKey === col.key && (
                    <span className={styles.sortArrow}>
                      {sortDir === 'asc' ? ' ▲' : ' ▼'}
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className={styles.empty}>
                  {emptyMessage ?? ja.no_data}
                </td>
              </tr>
            ) : (
              sorted.map((item) => (
                <tr
                  key={String(item[keyField])}
                  onClick={onRowClick ? () => onRowClick(item) : undefined}
                  className={onRowClick ? styles.clickable : undefined}
                >
                  {columns.map((col) => (
                    <td key={col.key}>{col.render(item)}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

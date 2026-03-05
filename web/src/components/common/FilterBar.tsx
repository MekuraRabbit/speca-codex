import { ja } from '@/i18n/ja';
import styles from './FilterBar.module.css';

interface FilterOption {
  value: string;
  label: string;
}

interface FilterDef {
  key: string;
  label: string;
  options: FilterOption[];
}

interface Props {
  filters: FilterDef[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
}

export function FilterBar({ filters, values, onChange }: Props) {
  return (
    <div className={styles.bar}>
      {filters.map((f) => (
        <label key={f.key} className={styles.filter}>
          <span className={styles.label}>{f.label}</span>
          <select
            value={values[f.key] ?? ''}
            onChange={(e) => onChange(f.key, e.target.value)}
            className={styles.select}
          >
            <option value="">{ja.filter_all}</option>
            {f.options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      ))}
    </div>
  );
}

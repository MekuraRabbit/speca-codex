import { ja } from '@/i18n/ja';
import { useBranches } from '@/hooks/useBranches';
import styles from './Header.module.css';

interface Props {
  branch: string | null;
  onBranchChange: (branch: string | null) => void;
  title?: string;
}

export function Header({ branch, onBranchChange, title }: Props) {
  const { branches, loading } = useBranches();

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        {title && <h1 className={styles.title}>{title}</h1>}
      </div>
      <div className={styles.right}>
        <label className={styles.branchLabel}>
          <span>{ja.run_selector_label}</span>
          <select
            value={branch ?? ''}
            onChange={(e) => onBranchChange(e.target.value || null)}
            className={styles.branchSelect}
            disabled={loading}
          >
            <option value="">{ja.dashboard_no_branch}</option>
            {branches.map((b) => (
              <option key={b.name} value={b.name}>
                {b.name}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}

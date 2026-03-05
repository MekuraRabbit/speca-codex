import { ja } from '@/i18n/ja';
import styles from './StatusIndicator.module.css';

export type Status = 'completed' | 'in_progress' | 'pending' | 'failed' | 'queued';

interface Props {
  status: Status;
  showLabel?: boolean;
}

const STATUS_LABELS: Record<Status, string> = {
  completed: ja.status_completed,
  in_progress: ja.status_in_progress,
  pending: ja.status_pending,
  failed: ja.status_failed,
  queued: ja.status_queued,
};

export function StatusIndicator({ status, showLabel = true }: Props) {
  return (
    <span className={`${styles.indicator} ${styles[status]}`}>
      <span className={styles.dot} />
      {showLabel && <span className={styles.label}>{STATUS_LABELS[status]}</span>}
    </span>
  );
}

export function workflowStatus(
  conclusion: string | null,
  status: string,
): Status {
  if (status === 'queued') return 'queued';
  if (status === 'in_progress' || status === 'waiting') return 'in_progress';
  if (conclusion === 'success') return 'completed';
  if (conclusion === 'failure') return 'failed';
  if (conclusion === 'cancelled') return 'failed';
  return 'pending';
}

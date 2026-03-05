import { severityColor, severityBgColor } from '@/lib/severity';
import styles from './SeverityBadge.module.css';

interface Props {
  severity: string;
}

export function SeverityBadge({ severity }: Props) {
  return (
    <span
      className={styles.badge}
      style={{
        color: severityColor(severity),
        backgroundColor: severityBgColor(severity),
      }}
    >
      {severity}
    </span>
  );
}

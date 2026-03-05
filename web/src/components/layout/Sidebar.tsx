import { NavLink } from 'react-router-dom';
import { ja } from '@/i18n/ja';
import styles from './Sidebar.module.css';

const NAV_ITEMS = [
  { to: '/', label: ja.nav_dashboard },
  { to: '/phase/01a', label: ja.nav_phase_01a },
  { to: '/phase/01b', label: ja.nav_phase_01b },
  { to: '/phase/01e', label: ja.nav_phase_01e },
  { to: '/phase/02c', label: ja.nav_phase_02c },
  { to: '/phase/03', label: ja.nav_phase_03 },
  { to: '/phase/04', label: ja.nav_phase_04 },
];

export function Sidebar() {
  return (
    <nav className={styles.sidebar}>
      <div className={styles.title}>{ja.app_title}</div>
      <ul className={styles.nav}>
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              className={({ isActive }) =>
                `${styles.link} ${isActive ? styles.active : ''}`
              }
              end={item.to === '/'}
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className={styles.bottom}>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `${styles.link} ${isActive ? styles.active : ''}`
          }
        >
          {ja.nav_settings}
        </NavLink>
      </div>
    </nav>
  );
}

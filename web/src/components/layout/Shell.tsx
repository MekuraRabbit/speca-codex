import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import styles from './Shell.module.css';

export function Shell() {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}

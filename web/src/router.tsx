import { createBrowserRouter } from 'react-router-dom';
import { Shell } from '@/components/layout/Shell';
import { DashboardPage } from '@/pages/DashboardPage';
import { PhasePage } from '@/pages/PhasePage';
import { PropertyPage } from '@/pages/PropertyPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { AuditWizardPage } from '@/pages/AuditWizardPage';

export const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [
      { path: '/', element: <DashboardPage /> },
      { path: '/audit', element: <AuditWizardPage /> },
      { path: '/phase/:phaseId', element: <PhasePage /> },
      { path: '/property/:propertyId', element: <PropertyPage /> },
      { path: '/settings', element: <SettingsPage /> },
    ],
  },
]);

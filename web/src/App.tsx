import { useState } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from '@/router';
import { TokenSetup } from '@/components/layout/TokenSetup';
import { getToken } from '@/lib/github-client';

export default function App() {
  const [configured, setConfigured] = useState(!!getToken());

  if (!configured) {
    return <TokenSetup onConfigured={() => setConfigured(true)} />;
  }

  return <RouterProvider router={router} />;
}

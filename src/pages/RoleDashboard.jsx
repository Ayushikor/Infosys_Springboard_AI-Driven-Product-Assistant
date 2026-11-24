import { useAuth } from '../context/AuthContext';

import Dashboard from './Dashboard';
import DeveloperDashboard from './DeveloperDashboard';
import ExecutiveDashboard from './ExecutiveDashboard';

export default function RoleDashboard() {
  const { user } = useAuth();

  const role = String(user?.role || 'Product Manager')
    .trim()
    .toLowerCase()
    .replace(/_/g, ' ');

  switch (role) {
    case 'developer':
      return <DeveloperDashboard />;

    case 'executive':
      return <ExecutiveDashboard />;

    default:
      // Preserve the existing Product Manager dashboard.
      // Admin currently receives the existing overview too.
      return <Dashboard />;
  }
}
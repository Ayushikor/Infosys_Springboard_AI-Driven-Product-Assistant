import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function NotFound() {
  const { isAuthenticated } = useAuth();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-6 text-center">
      <p className="text-sm font-semibold text-accent">404</p>
      <h1 className="mt-2 text-2xl font-semibold">Page not found</h1>
      <p className="mt-2 text-sm text-navy-500">The page you're looking for doesn't exist or was moved.</p>
      <Link to={isAuthenticated ? '/dashboard' : '/login'} className="btn-primary mt-6">Go to {isAuthenticated ? 'dashboard' : 'sign in'}</Link>
    </div>
  );
}

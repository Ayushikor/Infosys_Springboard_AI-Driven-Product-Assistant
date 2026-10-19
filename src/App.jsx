import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import { ProtectedRoute, PublicOnlyRoute } from './components/layout/ProtectedRoute';
import { useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import NotFound from './pages/NotFound';

// Feature pages are lazy-loaded so the first paint stays fast.
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Workspace = lazy(() => import('./pages/Workspace'));
const FeedbackUpload = lazy(() => import('./pages/FeedbackUpload'));
const FeedbackList = lazy(() => import('./pages/FeedbackList'));
const ThemesDashboard = lazy(() => import('./pages/ThemesDashboard'));
const Prioritization = lazy(() => import('./pages/Prioritization'));
const PRDViewer = lazy(() => import('./pages/PRDViewer'));
const Roadmap = lazy(() => import('./pages/Roadmap'));
const Chat = lazy(() => import('./pages/Chat'));
const Settings = lazy(() => import('./pages/Settings'));

const Loader = () => (
  <div className="flex h-64 items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-accent" role="status" aria-label="Loading" />
  </div>
);

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Suspense fallback={<Loader />}>
      <Routes>
        <Route path="/" element={<Navigate to={isAuthenticated ? '/dashboard' : '/login'} replace />} />
        <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
        <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />

        <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/workspace" element={<Workspace />} />
          <Route path="/feedback/upload" element={<FeedbackUpload />} />
          <Route path="/feedback" element={<FeedbackList />} />
          <Route path="/themes" element={<ThemesDashboard />} />
          <Route path="/prioritization" element={<Prioritization />} />
          <Route path="/prd" element={<PRDViewer />} />
          <Route path="/roadmap" element={<Roadmap />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

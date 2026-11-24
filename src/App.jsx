
import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import AppLayout from './components/layout/AppLayout';
import {
  ProtectedRoute,
  PublicOnlyRoute,
  RoleGuard,
} from './components/layout/ProtectedRoute';

import { useAuth } from './context/AuthContext';

import Login from './pages/Login';
import Register from './pages/Register';
import NotFound from './pages/NotFound';

// Role-specific dashboard
const RoleDashboard = lazy(() => import('./pages/RoleDashboard'));

// Feature pages
const Workspace = lazy(() => import('./pages/Workspace'));
const FeedbackUpload = lazy(() => import('./pages/FeedbackUpload'));
const FeedbackList = lazy(() => import('./pages/FeedbackList'));
const ThemesDashboard = lazy(() => import('./pages/ThemesDashboard'));
const Prioritization = lazy(() => import('./pages/Prioritization'));
const PRDViewer = lazy(() => import('./pages/PRDViewer'));
const Roadmap = lazy(() => import('./pages/Roadmap'));
const Chat = lazy(() => import('./pages/Chat'));
const Settings = lazy(() => import('./pages/Settings'));
const StrategyReport = lazy(() => import('./pages/StrategyReport'));
const AdminUsers = lazy(() => import('./pages/AdminUsers'));

// Role permissions
const ALL_ROLES = [
  'Admin',
  'Product Manager',
  'Developer',
  'Executive',
];

const PRODUCT_ROLES = [
  'Admin',
  'Product Manager',
];

const DELIVERY_ROLES = [
  'Admin',
  'Product Manager',
  'Developer',
];

const STRATEGY_ROLES = [
  'Admin',
  'Product Manager',
  'Executive',
];

const THEME_ROLES = [
  'Admin',
  'Product Manager',
  'Executive',
];

const withRoles = (roles, page) => (
  <RoleGuard allowedRoles={roles}>
    {page}
  </RoleGuard>
);

const Loader = () => (
  <div className="flex h-64 items-center justify-center">
    <div
      className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-200 border-t-accent"
      role="status"
      aria-label="Loading"
    />
  </div>
);

export default function App() {
  const { isAuthenticated } = useAuth();

  return (
    <Suspense fallback={<Loader />}>
      <Routes>

        {/* Public routes */}

        <Route
          path="/"
          element={
            <Navigate
              to={isAuthenticated ? '/dashboard' : '/login'}
              replace
            />
          }
        />

        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <Login />
            </PublicOnlyRoute>
          }
        />

        <Route
          path="/register"
          element={
            <PublicOnlyRoute>
              <Register />
            </PublicOnlyRoute>
          }
        />

        {/* Protected routes */}

        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >

          {/* Role-specific dashboards */}

          <Route
            path="/dashboard"
            element={withRoles(ALL_ROLES, <RoleDashboard />)}
          />

          {/* Workspace */}

          <Route
            path="/workspace"
            element={withRoles(ALL_ROLES, <Workspace />)}
          />

          {/* Feedback */}

          <Route
            path="/feedback/upload"
            element={withRoles(PRODUCT_ROLES, <FeedbackUpload />)}
          />

          <Route
            path="/feedback"
            element={withRoles(ALL_ROLES, <FeedbackList />)}
          />

          <Route
            path="/themes"
            element={withRoles(THEME_ROLES, <ThemesDashboard />)}
          />

          {/* Product management */}

          <Route
            path="/prioritization"
            element={withRoles(PRODUCT_ROLES, <Prioritization />)}
          />

          <Route
            path="/prd"
            element={withRoles(ALL_ROLES, <PRDViewer />)}
          />

          <Route
            path="/roadmap"
            element={withRoles(ALL_ROLES, <Roadmap />)}
          />

          {/* Strategy */}

          <Route
            path="/strategy-report"
            element={withRoles(STRATEGY_ROLES, <StrategyReport />)}
          />

          {/* AI Assistant */}

          <Route
            path="/chat"
            element={withRoles(DELIVERY_ROLES, <Chat />)}
          />

          {/* Settings */}

          <Route
            path="/settings"
            element={withRoles(ALL_ROLES, <Settings />)}
          />

          {/* Admin only */}

          <Route
            path="/admin/users"
            element={
              <RoleGuard allowedRoles={['Admin']}>
                <AdminUsers />
              </RoleGuard>
            }
          />

        </Route>

        {/* Not found */}

        <Route path="*" element={<NotFound />} />

      </Routes>
    </Suspense>
  );
}

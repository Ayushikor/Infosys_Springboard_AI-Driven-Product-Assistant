
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

// ---------------------------------------------------------
// PROTECTED ROUTE
// ---------------------------------------------------------

export function ProtectedRoute({ children }) {
  const {
    isAuthenticated,
    isLoading,
  } = useAuth();

  const location = useLocation();

  // Wait until session restoration finishes.
  if (isLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        role="status"
        aria-live="polite"
      >
        <p className="text-gray-500">
          Checking your session...
        </p>
      </div>
    );
  }

  // Redirect unauthenticated users to login.
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return children;
}

// ---------------------------------------------------------
// PUBLIC-ONLY ROUTE
// ---------------------------------------------------------

export function PublicOnlyRoute({ children }) {
  const {
    isAuthenticated,
    isLoading,
  } = useAuth();

  // Avoid redirecting before checking the session.
  if (isLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        role="status"
        aria-live="polite"
      >
        <p className="text-gray-500">
          Checking your session...
        </p>
      </div>
    );
  }

  // Already authenticated users go to dashboard.
  if (isAuthenticated) {
    return (
      <Navigate
        to="/dashboard"
        replace
      />
    );
  }

  return children;
}
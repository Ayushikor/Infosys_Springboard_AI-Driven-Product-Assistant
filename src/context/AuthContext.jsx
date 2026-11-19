
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { apiClient } from "../api/apiClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // -------------------------------------------------------
  // RESTORE EXISTING SESSION
  // -------------------------------------------------------

  const refreshUser = useCallback(async () => {
    try {
      const res = await apiClient.auth.currentUser?.();

      if (res?.success && res.data?.user) {
        setUser(res.data.user);
        return res.data.user;
      }

      setUser(null);
      return null;

    } catch (error) {
      console.error("Session restoration failed:", error);
      setUser(null);
      return null;

    } finally {
      setIsLoading(false);
    }
  }, []);

  // Check whether a valid login session exists on startup.
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // -------------------------------------------------------
  // LOGIN
  // -------------------------------------------------------

  const login = useCallback(
    async (email, password, remember) => {
      const res = await apiClient.auth.login(
        email,
        password,
        remember
      );

      if (res?.success && res.data?.user) {
        setUser(res.data.user);
      }

      return res;
    },
    []
  );

  // -------------------------------------------------------
  // REGISTER
  // -------------------------------------------------------

  const register = useCallback(
    async (payload) => {
      return apiClient.auth.register(payload);
    },
    []
  );

  // -------------------------------------------------------
  // LOGOUT
  // -------------------------------------------------------

  const logout = useCallback(async () => {
    try {
      return await apiClient.auth.logout();
    } finally {
      setUser(null);
    }
  }, []);

  // -------------------------------------------------------
  // CONTEXT VALUE
  // -------------------------------------------------------

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
      refreshUser,
    }),
    [
      user,
      isLoading,
      login,
      register,
      logout,
      refreshUser,
    ]
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------
// CUSTOM AUTH HOOK
// ---------------------------------------------------------

export const useAuth = () => {
  const ctx = useContext(AuthContext);

  if (!ctx) {
    throw new Error(
      "useAuth must be used inside AuthProvider"
    );
  }

  return ctx;
};

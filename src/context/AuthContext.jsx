import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { apiClient } from '../api/apiClient';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Read the session synchronously so protected routes don't flash the login page on refresh.
  const [user, setUser] = useState(() => apiClient.auth.currentUser?.() ?? null);

  const login = useCallback(async (email, password, remember) => {
    const res = await apiClient.auth.login(email, password, remember);
    if (res.success) setUser(res.data.user);
    return res;
  }, []);

  const register = useCallback((payload) => apiClient.auth.register(payload), []);

  const logout = useCallback(async () => {
    await apiClient.auth.logout();
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, isAuthenticated: !!user, login, register, logout }), [user, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
};

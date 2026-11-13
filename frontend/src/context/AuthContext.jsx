import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { authApi } from '../api';
import { TOKEN_KEY, USER_KEY } from '../api/client';

const AuthContext = createContext(null);

export const ROLE_HOME = {
  customer: '/restaurants',
  restaurant_owner: '/owner',
  delivery_partner: '/delivery',
};

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY));
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (localStorage.getItem(TOKEN_KEY) ? readUser() : null));

  const persist = useCallback(({ access_token: token, user: u }) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(u));
    setUser(u);
    return u;
  }, []);

  const login = useCallback(async (email, password) => persist(await authApi.login({ email, password })), [persist]);
  const register = useCallback(async (body) => persist(await authApi.register(body)), [persist]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setUser(null);
  }, []);

  // The axios interceptor fires this when the token is rejected (expired etc.)
  useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener('campusbite:logout', handler);
    return () => window.removeEventListener('campusbite:logout', handler);
  }, []);

  const value = useMemo(() => ({ user, login, register, logout }), [user, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

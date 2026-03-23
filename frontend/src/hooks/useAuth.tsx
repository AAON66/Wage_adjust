import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import type { LoginPayload, RegisterPayload, UserProfile } from '../types/api';
import {
  AUTH_SESSION_EVENT,
  clearAuthStorage,
  fetchCurrentUser,
  getStoredAccessToken,
  getStoredRefreshToken,
  getStoredUser,
  login as loginRequest,
  refresh as refreshRequest,
  register as registerRequest,
  storeAuthSession,
  updateStoredTokens,
  updateStoredUser,
} from '../services/auth';

type AuthContextValue = {
  user: UserProfile | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (payload: LoginPayload) => Promise<UserProfile>;
  register: (payload: RegisterPayload) => Promise<UserProfile>;
  refreshProfile: () => Promise<UserProfile | null>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(() => getStoredUser());
  const [accessToken, setAccessToken] = useState<string | null>(() => getStoredAccessToken());
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const storedRefreshToken = getStoredRefreshToken();
      const storedToken = getStoredAccessToken();
      const storedUser = getStoredUser();

      if (!storedRefreshToken || !storedToken || !storedUser) {
        clearAuthStorage();
        if (!cancelled) {
          setUser(null);
          setAccessToken(null);
          setIsBootstrapping(false);
        }
        return;
      }

      try {
        const profile = await fetchCurrentUser(storedToken);
        if (!cancelled) {
          updateStoredUser(profile);
          setUser(profile);
          setAccessToken(storedToken);
        }
      } catch {
        try {
          const refreshedTokens = await refreshRequest(storedRefreshToken);
          updateStoredTokens(refreshedTokens);
          const profile = await fetchCurrentUser(refreshedTokens.access_token);
          if (!cancelled) {
            updateStoredUser(profile);
            setUser(profile);
            setAccessToken(refreshedTokens.access_token);
          }
        } catch {
          clearAuthStorage();
          if (!cancelled) {
            setUser(null);
            setAccessToken(null);
          }
        }
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function syncAuthState() {
      setUser(getStoredUser());
      setAccessToken(getStoredAccessToken());
    }

    window.addEventListener(AUTH_SESSION_EVENT, syncAuthState);
    return () => {
      window.removeEventListener(AUTH_SESSION_EVENT, syncAuthState);
    };
  }, []);

  async function handleRegister(payload: RegisterPayload): Promise<UserProfile> {
    const response = await registerRequest(payload);
    storeAuthSession(response);
    setUser(response.user);
    setAccessToken(response.tokens.access_token);
    return response.user;
  }

  async function handleLogin(payload: LoginPayload): Promise<UserProfile> {
    const tokens = await loginRequest(payload);
    const profile = await fetchCurrentUser(tokens.access_token);
    storeAuthSession({ user: profile, tokens });
    setUser(profile);
    setAccessToken(tokens.access_token);
    return profile;
  }

  async function refreshProfile(): Promise<UserProfile | null> {
    const token = accessToken ?? getStoredAccessToken();
    if (!token) {
      return null;
    }
    const profile = await fetchCurrentUser(token);
    updateStoredUser(profile);
    setUser(profile);
    return profile;
  }

  function logout() {
    clearAuthStorage();
    setUser(null);
    setAccessToken(null);
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      accessToken,
      isAuthenticated: Boolean(user && accessToken),
      isBootstrapping,
      login: handleLogin,
      register: handleRegister,
      refreshProfile,
      logout,
    }),
    [accessToken, isBootstrapping, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }
  return context;
}

import api from './api';
import type { AuthResponse, LoginPayload, RegisterPayload, TokenPair, UserProfile } from '../types/api';

const ACCESS_TOKEN_KEY = 'wage_adjust.access_token';
const REFRESH_TOKEN_KEY = 'wage_adjust.refresh_token';
const USER_KEY = 'wage_adjust.user';

export function getStoredAccessToken(): string | null {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): UserProfile | null {
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    clearAuthStorage();
    return null;
  }
}

export function storeAuthSession(auth: AuthResponse): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, auth.tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, auth.tokens.refresh_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(auth.user));
}

export function updateStoredTokens(tokens: TokenPair): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearAuthStorage(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const response = await api.post<AuthResponse>('/auth/register', payload);
  return response.data;
}

export async function login(payload: LoginPayload): Promise<TokenPair> {
  const response = await api.post<TokenPair>('/auth/login', payload);
  return response.data;
}

export async function refresh(refreshToken: string): Promise<TokenPair> {
  const response = await api.post<TokenPair>('/auth/refresh', { refresh_token: refreshToken });
  return response.data;
}

export async function fetchCurrentUser(token?: string): Promise<UserProfile> {
  const accessToken = token ?? getStoredAccessToken();
  const response = await api.get<UserProfile>('/auth/me', {
    headers: accessToken
      ? {
          Authorization: `Bearer ${accessToken}`,
        }
      : undefined,
  });
  return response.data;
}

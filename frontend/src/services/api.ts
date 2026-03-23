import axios, { type InternalAxiosRequestConfig } from 'axios';

const ACCESS_TOKEN_KEY = 'wage_adjust.access_token';
const REFRESH_TOKEN_KEY = 'wage_adjust.refresh_token';
const USER_KEY = 'wage_adjust.user';
const AUTH_SESSION_EVENT = 'wage_adjust.auth_changed';

type RetryableRequestConfig = InternalAxiosRequestConfig & {
  _retry?: boolean;
};

let refreshInFlight: Promise<string | null> | null = null;

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8011/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = window.localStorage.getItem(ACCESS_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) {
    return null;
  }

  const response = await axios.post<{ access_token: string; refresh_token: string }>(
    `${api.defaults.baseURL}/auth/refresh`,
    { refresh_token: refreshToken },
    {
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    },
  );

  const { access_token: accessToken, refresh_token: nextRefreshToken } = response.data;
  window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, nextRefreshToken);
  window.dispatchEvent(new Event(AUTH_SESSION_EVENT));
  return accessToken;
}

function clearAuthSession() {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.dispatchEvent(new Event(AUTH_SESSION_EVENT));
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status as number | undefined;
    const originalRequest = error.config as RetryableRequestConfig | undefined;

    if (status !== 401 || !originalRequest || originalRequest._retry) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      refreshInFlight ??= refreshAccessToken().finally(() => {
        refreshInFlight = null;
      });
      const nextAccessToken = await refreshInFlight;

      if (!nextAccessToken) {
        clearAuthSession();
        return Promise.reject(error);
      }

      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
      } else {
        originalRequest.headers = { Authorization: `Bearer ${nextAccessToken}` } as RetryableRequestConfig['headers'];
      }
      return api(originalRequest);
    } catch (refreshError) {
      clearAuthSession();
      return Promise.reject(refreshError);
    }
  },
);

export default api;

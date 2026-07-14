import type { AxiosError, InternalAxiosRequestConfig } from 'axios';

import { apiClient } from '@/lib/axios';

type RequestWithRetry = InternalAxiosRequestConfig & { _retry?: boolean };

type AuthInterceptorOptions = {
  getAccessToken: () => Promise<string | null>;
  refreshAccessToken: () => Promise<string | null>;
};

let isConfigured = false;

function setAuthorizationHeader(
  headers: InternalAxiosRequestConfig['headers'],
  token: string,
): void {
  if (!headers) {
    return;
  }

  if (typeof headers.set === 'function') {
    headers.set('Authorization', `Bearer ${token}`);
    return;
  }

  headers.Authorization = `Bearer ${token}`;
}

function removeAuthorizationHeader(headers: InternalAxiosRequestConfig['headers']): void {
  if (!headers) {
    return;
  }

  if (typeof headers.delete === 'function') {
    headers.delete('Authorization');
    return;
  }

  delete headers.Authorization;
}

export class ApiError extends Error {
  status?: number;
  code?: string;
  detail?: string;

  constructor(message: string, status?: number, code?: string, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

export function configureApiAuthInterceptors(options: AuthInterceptorOptions): void {
  if (isConfigured) {
    return;
  }

  apiClient.interceptors.request.use(async (config) => {
    const token = await options.getAccessToken();

    if (token) {
      setAuthorizationHeader(config.headers, token);
    } else {
      removeAuthorizationHeader(config.headers);
    }

    return config;
  });

  apiClient.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const statusCode = error.response?.status;
      const originalRequest = error.config as RequestWithRetry | undefined;

      // Handle 401 Unauthorized by trying to refresh session token
      if (statusCode === 401 && originalRequest && !originalRequest._retry) {
        originalRequest._retry = true;
        const refreshedToken = await options.refreshAccessToken();

        if (refreshedToken) {
          setAuthorizationHeader(originalRequest.headers, refreshedToken);
          return apiClient(originalRequest);
        }
      }

      // Map connection timeouts, offline errors, and HTTP statuses to ApiError
      let message = 'An unexpected error occurred.';
      const code = error.code;
      let detail: string | undefined;

      if (error.code === 'ECONNABORTED') {
        message = 'Request timed out. Please check your network and try again.';
      } else if (!error.response) {
        message = 'Network connection failed. Check your internet connection.';
      } else {
        const responseData = error.response.data as any;
        detail =
          typeof responseData === 'object'
            ? responseData?.detail || responseData?.message
            : undefined;

        switch (statusCode) {
          case 403:
            message = 'Permission denied. You do not have access to this resource.';
            break;
          case 404:
            message = 'Resource not found.';
            break;
          case 500:
            message = 'Internal server error. Please try again later.';
            break;
          default:
            if (detail) {
              message = detail;
            }
            break;
        }
      }

      return Promise.reject(new ApiError(message, statusCode, code, detail));
    },
  );

  isConfigured = true;
}

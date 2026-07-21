import type {
  AuthUser,
  Fault,
  LoginResponse,
  OdometerReading,
  Paginated,
  RefreshTokenResponse,
  RepairOrder,
  Vehicle,
  VehicleSummary,
  VehicleStatus,
} from '../types/fmms';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'fmms_access_token';
const REFRESH_TOKEN_KEY = 'fmms_refresh_token';
const ACCESS_EXPIRES_AT_KEY = 'fmms_access_expires_at';
const REFRESH_EXPIRES_AT_KEY = 'fmms_refresh_expires_at';
const REFRESH_SKEW_MS = 60_000;

type ApiRequestInit = RequestInit & {
  auth?: boolean;
  retryOnUnauthorized?: boolean;
};

let refreshPromise: Promise<string> | null = null;

export function getAccessToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function setAccessToken(token: string): void {
  if (token.trim()) localStorage.setItem(TOKEN_KEY, token.trim());
  else localStorage.removeItem(TOKEN_KEY);
}

export function setAccessTokenExpiresAt(expiresAt: string): void {
  if (expiresAt.trim()) localStorage.setItem(ACCESS_EXPIRES_AT_KEY, expiresAt.trim());
  else localStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
}

export function setRefreshToken(token: string): void {
  if (token.trim()) localStorage.setItem(REFRESH_TOKEN_KEY, token.trim());
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function setRefreshTokenExpiresAt(expiresAt: string): void {
  if (expiresAt.trim()) localStorage.setItem(REFRESH_EXPIRES_AT_KEY, expiresAt.trim());
  else localStorage.removeItem(REFRESH_EXPIRES_AT_KEY);
}

export function setAuthSession(response: LoginResponse): void {
  setAccessToken(response.access);
  setRefreshToken(response.refresh);
  setAccessTokenExpiresAt(response.access_expires_at);
  setRefreshTokenExpiresAt(response.refresh_expires_at);
}

export function clearAuthTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(ACCESS_EXPIRES_AT_KEY);
  localStorage.removeItem(REFRESH_EXPIRES_AT_KEY);
}

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_TOKEN_KEY) ?? '';
}

function isExpiredOrNear(expiresAt: string): boolean {
  const timestamp = Date.parse(expiresAt);
  if (Number.isNaN(timestamp)) return true;
  return timestamp - Date.now() <= REFRESH_SKEW_MS;
}

function shouldRefreshAccessToken(): boolean {
  const access = getAccessToken();
  const refresh = getRefreshToken();
  const refreshExpiresAt = localStorage.getItem(REFRESH_EXPIRES_AT_KEY) ?? '';
  if (!access || !refresh) return false;
  if (refreshExpiresAt && isExpiredOrNear(refreshExpiresAt)) {
    clearAuthTokens();
    return false;
  }
  const accessExpiresAt = localStorage.getItem(ACCESS_EXPIRES_AT_KEY) ?? '';
  return !accessExpiresAt || isExpiredOrNear(accessExpiresAt);
}

async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;
  const refresh = getRefreshToken();
  if (!refresh) {
    clearAuthTokens();
    throw new ApiError(401, 'نشست کاربری منقضی شده است.', null);
  }

  refreshPromise = fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  })
    .then(async (response) => {
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (!response.ok) {
        clearAuthTokens();
        const message = data?.message ?? data?.detail ?? 'نشست کاربری منقضی شده است.';
        throw new ApiError(response.status, message, data);
      }
      const payload = data as RefreshTokenResponse;
      setAccessToken(payload.access);
      setAccessTokenExpiresAt(payload.access_expires_at);
      return payload.access;
    })
    .finally(() => {
      refreshPromise = null;
    });

  return refreshPromise;
}

async function getValidAccessToken(): Promise<string> {
  if (shouldRefreshAccessToken()) {
    return refreshAccessToken();
  }
  return getAccessToken();
}

async function request<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const { auth = true, retryOnUnauthorized = true, ...fetchInit } = init;
  const token = auth ? await getValidAccessToken() : '';
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...fetchInit,
    headers,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (response.status === 401 && auth && retryOnUnauthorized && getRefreshToken()) {
    const refreshedToken = await refreshAccessToken();
    return request<T>(path, {
      ...fetchInit,
      headers: {
        ...Object.fromEntries(headers.entries()),
        Authorization: `Bearer ${refreshedToken}`,
      },
      auth,
      retryOnUnauthorized: false,
    });
  }
  if (!response.ok) {
    const message =
      data?.message ??
      data?.detail ??
      data?.messages?.[0] ??
      `خطای ${response.status} در ارتباط با سرور`;
    throw new ApiError(response.status, message, data);
  }
  return data as T;
}

export const api = {
  login(username: string, password: string) {
    return request<LoginResponse>('/auth/token/', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
      auth: false,
    });
  },

  me() {
    return request<AuthUser>('/auth/me/');
  },

  getVehicleSummary() {
    return request<VehicleSummary>('/vehicles/summary/');
  },

  listVehicles(status?: VehicleStatus | '', ordering = '-created_at') {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (ordering) params.set('ordering', ordering);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<Paginated<Vehicle>>(`/vehicles/${query}`);
  },

  getVehicle(id: string) {
    return request<Vehicle>(`/vehicles/${id}/`);
  },

  updateVehicleStatus(id: string, status: VehicleStatus) {
    return request<Vehicle>(`/vehicles/${id}/status/`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    });
  },

  getOdometerHistory(vehicleId: string) {
    return request<OdometerReading[]>(`/vehicles/${vehicleId}/odometer-history/`);
  },

  recordOdometer(vehicleId: string, payload: { reading_date: string; odometer_km: number }) {
    return request<OdometerReading>(`/vehicles/${vehicleId}/odometer/`, {
      method: 'POST',
      body: JSON.stringify({ ...payload, source: 'DRIVER' }),
    });
  },

  listFaults(vehicleId: string) {
    return request<Paginated<Fault>>(`/faults/?vehicle_id=${vehicleId}`);
  },

  listRepairOrders(vehicleId: string) {
    return request<Paginated<RepairOrder>>(`/repair-orders/?vehicle_id=${vehicleId}`);
  },

  setAccessToken,
  setRefreshToken,
  setAuthSession,
  getAccessToken,
  clearAuthTokens,
};

import type { AuthUser, Fault, LoginResponse, OdometerReading, Paginated, RepairOrder, Vehicle, VehicleStatus } from '../types/fmms';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const TOKEN_KEY = 'fmms_access_token';
const REFRESH_TOKEN_KEY = 'fmms_refresh_token';

export function getAccessToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? '';
}

export function setAccessToken(token: string): void {
  if (token.trim()) localStorage.setItem(TOKEN_KEY, token.trim());
  else localStorage.removeItem(TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  if (token.trim()) localStorage.setItem(REFRESH_TOKEN_KEY, token.trim());
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function clearAuthTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
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
    });
  },

  me() {
    return request<AuthUser>('/auth/me/');
  },

  listVehicles(status?: VehicleStatus | '') {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return request<Paginated<Vehicle>>(`/vehicles/${query}`);
  },

  getVehicle(id: string) {
    return request<Vehicle>(`/vehicles/${id}/`);
  },

  updateVehicleStatus(id: string, status: VehicleStatus) {
    return request<Vehicle>(`/vehicles/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    });
  },

  getOdometerHistory(vehicleId: string) {
    return request<OdometerReading[]>(`/vehicles/${vehicleId}/odometer/`);
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
  getAccessToken,
  clearAuthTokens,
};

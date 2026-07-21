export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_staff: boolean;
  is_superuser: boolean;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  token_type: string;
  access_expires_at: string;
  refresh_expires_at: string;
  user: AuthUser;
}

export interface RefreshTokenResponse {
  access: string;
  token_type: string;
  access_expires_at: string;
}

export type VehicleStatus =
  | 'ACTIVE'
  | 'INACTIVE'
  | 'UNDER_REPAIR'
  | 'WAITING_DRIVER_CONFIRMATION'
  | 'SUSPENDED'
  | 'OUT_OF_SERVICE'
  | 'DECOMMISSIONED';

export interface AssignedVehicleDriver {
  customer_number: string;
  name: string | null;
}

export interface Vehicle {
  id: string;
  vehicle_number: string;
  license_plate: string;
  status: VehicleStatus;
  status_label: string;
  created_at: string;
  updated_at: string;
  commissioning_date: string | null;
  driver1: AssignedVehicleDriver | null;
  driver2: AssignedVehicleDriver | null;
}

export interface VehicleSummary {
  active_fleet_count: number;
  operational_fleet_count: number;
  under_repair_fleet_count: number;
  unusable_fleet_count: number;
  last_sap_sync_at: string | null;
  average_odometer_km: number;
  average_faults_last_30_days: number;
}

export interface OdometerReading {
  id: string;
  vehicle_id: string;
  reading_date: string;
  odometer_km: number;
  source: string;
  recorded_by: string;
  recorded_at: string;
  updated_at: string;
}

export interface Fault {
  id: string;
  vehicle_id: string;
  code: string;
  description: string;
  severity: string;
  status: string;
  reported_at?: string;
  created_at?: string;
}

export interface RepairOrder {
  id: string;
  vehicle_id: string;
  fault_id: string;
  status: string;
  workshop_type?: string;
  workshop_id?: string;
  sap_order_number?: string;
  updated_at?: string;
  completed_at?: string | null;
  parts?: RepairPart[];
  activities?: RepairActivity[];
}

export interface RepairPart {
  part_id: string;
  material_number: string;
  quantity: number;
  unit_of_measure: string;
}

export interface RepairActivity {
  activity_id: string;
  description: string;
  labor_hours: string | number;
  performed_at: string;
}

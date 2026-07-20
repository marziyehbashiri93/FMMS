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
  user: AuthUser;
}

export type VehicleStatus =
  | 'ACTIVE'
  | 'INACTIVE'
  | 'UNDER_REPAIR'
  | 'WAITING_DRIVER_CONFIRMATION'
  | 'SUSPENDED'
  | 'OUT_OF_SERVICE'
  | 'DECOMMISSIONED';

export interface Vehicle {
  id: string;
  plate_number: string;
  vin: string;
  make: string;
  model: string;
  year: number;
  category: string;
  status: VehicleStatus;
  status_label: string;
  created_at: string;
  updated_at: string;
  chassis_number: string | null;
  sap_equipment_number: string | null;
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

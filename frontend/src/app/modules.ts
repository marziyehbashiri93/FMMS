import {
  Assessment,
  Build,
  CalendarMonth,
  CarRepair,
  Dashboard,
  DirectionsCar,
  Handshake,
  Inventory2,
  LocalShipping,
  PeopleAlt,
  ReportProblem,
  Settings,
  Sync,
  Widgets,
} from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';

export interface AppModule {
  key: string;
  label: string;
  path: string;
  icon: SvgIconComponent;
  enabled: boolean;
}

export const modules: AppModule[] = [
  { key: 'dashboard', label: 'داشبورد', path: '/dashboard', icon: Dashboard, enabled: false },
  { key: 'vehicles', label: 'خودروها', path: '/vehicles', icon: DirectionsCar, enabled: true },
  { key: 'components', label: 'کامپوننت‌ها', path: '/components', icon: Widgets, enabled: true },
  { key: 'drivers', label: 'راننده‌ها', path: '/drivers', icon: PeopleAlt, enabled: false },
  { key: 'inspections', label: 'بازرسی‌ها', path: '/inspections', icon: ReportProblem, enabled: false },
  { key: 'faults', label: 'خرابی‌ها', path: '/faults', icon: CarRepair, enabled: false },
  { key: 'repairs', label: 'تعمیرات', path: '/repairs', icon: Build, enabled: false },
  { key: 'materials', label: 'قطعات و انبار', path: '/materials', icon: Inventory2, enabled: false },
  { key: 'procurement', label: 'تدارکات', path: '/procurement', icon: LocalShipping, enabled: false },
  { key: 'pm', label: 'نگهداری پیشگیرانه', path: '/pm', icon: CalendarMonth, enabled: false },
  { key: 'handover', label: 'تحویل و تایید', path: '/handover', icon: Handshake, enabled: false },
  { key: 'sap', label: 'یکپارچه‌سازی SAP', path: '/sap', icon: Sync, enabled: false },
  { key: 'reports', label: 'گزارش‌ها', path: '/reports', icon: Assessment, enabled: false },
  { key: 'settings', label: 'تنظیمات', path: '/settings', icon: Settings, enabled: false },
];

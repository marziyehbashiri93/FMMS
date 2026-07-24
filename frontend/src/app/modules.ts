import {
  Assessment,
  Build,
  CalendarMonth,
  CarRepair,
  Dashboard,
  DirectionsCar,
  FactCheck,
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

export interface NavGroup {
  key: string;
  label: string;
  icon: SvgIconComponent;
  children: AppModule[];
}

export type NavEntry = AppModule | NavGroup;

export function isNavGroup(entry: NavEntry): entry is NavGroup {
  return 'children' in entry;
}

export const modules: AppModule[] = [
  { key: 'dashboard', label: 'داشبورد', path: '/dashboard', icon: Dashboard, enabled: false },
  { key: 'vehicles', label: 'لیست خودروها', path: '/vehicles', icon: DirectionsCar, enabled: true },
  { key: 'checklists', label: 'لیست بازرسی روزانه', path: '/checklists', icon: FactCheck, enabled: true },
  { key: 'components', label: 'کامپوننت‌ها', path: '/components', icon: Widgets, enabled: true },
  { key: 'drivers', label: 'لیست راننده‌ها', path: '/drivers', icon: PeopleAlt, enabled: true },
  { key: 'inspections', label: 'بازرسی روزانه', path: '/inspections', icon: ReportProblem, enabled: true },
  { key: 'faults', label: 'ثبت خرابی', path: '/faults', icon: CarRepair, enabled: true },
  { key: 'repairs', label: 'تعمیرات', path: '/repairs', icon: Build, enabled: false },
  { key: 'materials', label: 'قطعات و انبار', path: '/materials', icon: Inventory2, enabled: false },
  { key: 'procurement', label: 'تدارکات', path: '/procurement', icon: LocalShipping, enabled: false },
  { key: 'pm', label: 'نگهداری پیشگیرانه', path: '/pm', icon: CalendarMonth, enabled: false },
  { key: 'handover', label: 'تحویل و تایید', path: '/handover', icon: Handshake, enabled: false },
  { key: 'sap', label: 'یکپارچه‌سازی SAP', path: '/sap', icon: Sync, enabled: false },
  { key: 'reports', label: 'گزارش‌ها', path: '/reports', icon: Assessment, enabled: false },
  { key: 'settings', label: 'تنظیمات', path: '/settings', icon: Settings, enabled: false },
];

const byKey = (key: string): AppModule => {
  const mod = modules.find((item) => item.key === key);
  if (!mod) throw new Error(`Unknown module: ${key}`);
  return mod;
};

/** Sidebar / drawer navigation tree (supports nested groups). */
export const navSections: Array<{ label: string; entries: NavEntry[] }> = [
  {
    label: 'اصلی',
    entries: [
      byKey('dashboard'),
      {
        key: 'vehicle',
        label: 'خودرو',
        icon: DirectionsCar,
        children: [byKey('vehicles'), byKey('checklists')],
      },
      byKey('components'),
      {
        key: 'driver',
        label: 'راننده',
        icon: PeopleAlt,
        children: [byKey('drivers'), byKey('inspections'), byKey('faults')],
      },
    ],
  },
  {
    label: 'مدیریت',
    entries: modules.filter(
      (item) =>
        ![
          'dashboard',
          'vehicles',
          'checklists',
          'components',
          'drivers',
          'inspections',
          'faults',
        ].includes(item.key),
    ),
  },
];

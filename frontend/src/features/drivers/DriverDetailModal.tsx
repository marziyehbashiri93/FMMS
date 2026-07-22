import { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  Link,
  Stack,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { Person } from '@mui/icons-material';
import { api } from '../../api/client';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { DriverStatusBadge } from '../../components/DriverStatusBadge';
import { JalaliDateField } from '../../components/JalaliDateField';
import { ErrorState, LoadingState } from '../../components/States';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type {
  Driver,
  DriverAssignedVehicle,
  DriverVehicleAssignmentHistoryItem,
} from '../../types/fmms';
import { formatDateTime } from '../../utils/format';

const ROLE_LABELS: Record<string, string> = {
  DRIVER: 'راننده اصلی',
  ASSISTANT: 'کمک راننده',
};

const GENDER_LABELS: Record<string, string> = {
  MALE: 'مرد',
  FEMALE: 'زن',
  male: 'مرد',
  female: 'زن',
};

function VehiclePlateLink({ vehicle }: { vehicle: DriverAssignedVehicle }) {
  const plate = vehicle.license_plate || vehicle.vehicle_number || '—';
  return (
    <Link
      component={RouterLink}
      to={`/vehicles?vehicleId=${encodeURIComponent(vehicle.id)}`}
      underline="hover"
      fontWeight={800}
    >
      {plate}
    </Link>
  );
}

type HistorySortKey = 'synced_at' | 'vehicle_number' | 'license_plate' | 'driver_role';

/**
 * Driver detail modal (Vehicle-style tabs).
 */
export function DriverDetailModal({
  open,
  driverId,
  onClose,
}: {
  open: boolean;
  driverId: string | null;
  onClose: () => void;
}) {
  const [driver, setDriver] = useState<Driver | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<DriverVehicleAssignmentHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyDate, setHistoryDate] = useState('');
  const [tab, setTab] = useState(0);
  const [orderBy, setOrderBy] = useState<HistorySortKey>('synced_at');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');

  const loadDriver = async (id: string) => {
    setLoading(true);
    setError('');
    try {
      setDriver(await api.getDriver(id));
    } catch (err) {
      setDriver(null);
      setError(err instanceof Error ? err.message : 'خطا در دریافت جزئیات راننده');
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async (id: string, date = historyDate) => {
    setHistoryLoading(true);
    setHistoryError('');
    try {
      setHistory(
        await api.getDriverVehicleAssignmentHistory(id, {
          fromDate: date || undefined,
        }),
      );
    } catch (err) {
      setHistory([]);
      setHistoryError(err instanceof Error ? err.message : 'خطا در دریافت تاریخچه تخصیص');
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    if (!open || !driverId) return;
    setTab(0);
    setHistoryDate('');
    void loadDriver(driverId);
    void loadHistory(driverId, '');
  }, [open, driverId]);

  const sortedHistory = [...history].sort((a, b) => {
    const dir = order === 'asc' ? 1 : -1;
    const left = String(a[orderBy] ?? '');
    const right = String(b[orderBy] ?? '');
    return left.localeCompare(right, 'fa') * dir;
  });

  const historyColumns: Array<RtlDataTableColumn<DriverVehicleAssignmentHistoryItem, HistorySortKey>> = [
    {
      key: 'synced_at',
      label: 'تاریخ تخصیص',
      sortable: true,
      render: (row) => formatDateTime(row.synced_at),
    },
    {
      key: 'vehicle_number',
      label: 'شناسه خودرو',
      sortable: true,
    },
    {
      key: 'license_plate',
      label: 'پلاک',
      sortable: true,
    },
    {
      key: 'driver_role',
      label: 'نقش',
      sortable: true,
      render: (row) => ROLE_LABELS[row.driver_role] ?? row.driver_role,
    },
  ];

  const asDriver = driver?.current_vehicle_as_driver;
  const asAssistant = driver?.current_vehicle_as_assistant;

  const tabs = driver
    ? [
        {
          label: 'اطلاعات پایه',
          content: (
            <Card
              variant="outlined"
              sx={{
                borderColor: 'rgba(184, 197, 188, 0.9)',
                borderRadius: (t) => t.radius('md'),
                boxShadow: '0 8px 24px rgba(31, 79, 57, 0.05)',
              }}
            >
              <CardContent sx={{ p: { xs: 1.75, sm: 2.25 }, '&:last-child': { pb: { xs: 1.75, sm: 2.25 } } }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
                  <Typography variant="h3">اطلاعات پایه</Typography>
                  <DriverStatusBadge status={driver.status} />
                </Stack>
                <DetailLine label="شناسه داخلی" value={<Typography variant="body2">{driver.id}</Typography>} />
                <DetailLine
                  label="شناسه راننده"
                  value={<Typography fontWeight={800}>{driver.customer_number}</Typography>}
                />
                <DetailLine label="نام" value={<Typography variant="body2">{driver.name}</Typography>} />
                <DetailLine
                  label="موبایل"
                  value={<Typography variant="body2">{driver.mobile || '—'}</Typography>}
                />
                <DetailLine
                  label="شماره پرسنلی"
                  value={<Typography variant="body2">{driver.personnel_number || '—'}</Typography>}
                />
                <DetailLine
                  label="جنسیت"
                  value={
                    <Typography variant="body2">
                      {driver.gender ? GENDER_LABELS[driver.gender] ?? driver.gender : '—'}
                    </Typography>
                  }
                />
                <DetailLine
                  label="کد نیلوفر"
                  value={<Typography variant="body2">{driver.nilofar_code || '—'}</Typography>}
                />
                {asDriver && (
                  <>
                    <DetailLine
                      label="نقش"
                      value={<Typography variant="body2">{ROLE_LABELS.DRIVER}</Typography>}
                    />
                    <DetailLine label="پلاک" value={<VehiclePlateLink vehicle={asDriver} />} />
                  </>
                )}
                {asAssistant && (
                  <>
                    <DetailLine
                      label="نقش"
                      value={<Typography variant="body2">{ROLE_LABELS.ASSISTANT}</Typography>}
                    />
                    <DetailLine label="پلاک" value={<VehiclePlateLink vehicle={asAssistant} />} />
                  </>
                )}
                {!asDriver && !asAssistant && (
                  <>
                    <DetailLine label="نقش" value={<Typography variant="body2">—</Typography>} />
                    <DetailLine label="پلاک" value={<Typography variant="body2">—</Typography>} />
                  </>
                )}
              </CardContent>
            </Card>
          ),
        },
        {
          label: 'تاریخچه تخصیص',
          content: (
            <Stack spacing={1.5}>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                useFlexGap
                alignItems={{ xs: 'stretch', sm: 'center' }}
                sx={{ gap: 2, '& > *': { margin: 0 } }}
              >
                <JalaliDateField
                  label="تاریخ"
                  value={historyDate}
                  onChange={(next) => {
                    setHistoryDate(next);
                    if (driverId) void loadHistory(driverId, next);
                  }}
                  sx={{ width: { xs: '100%', sm: 220 }, flexShrink: 0 }}
                />
                <ClearFiltersButton
                  disabled={!historyDate || historyLoading}
                  onClick={() => {
                    setHistoryDate('');
                    if (driverId) void loadHistory(driverId, '');
                  }}
                />
              </Stack>
              {historyLoading && <LoadingState label="در حال دریافت تاریخچه" />}
              {historyError && (
                <ErrorState
                  message={historyError}
                  onRetry={() => driverId && void loadHistory(driverId)}
                />
              )}
              {!historyLoading && !historyError && (
                <RtlDataTable
                  columns={historyColumns}
                  rows={sortedHistory}
                  getRowKey={(row) => row.id}
                  orderBy={orderBy}
                  order={order}
                  onSort={(key) => {
                    if (orderBy === key) {
                      setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
                      return;
                    }
                    setOrderBy(key);
                    setOrder('asc');
                  }}
                  emptyMessage="تاریخچه‌ای یافت نشد"
                  minWidth={560}
                />
              )}
            </Stack>
          ),
        },
      ]
    : [];

  return (
    <TabbedDetailModal
      open={open}
      onClose={onClose}
      title="جزئیات راننده"
      icon={Person}
      tabs={tabs}
      loading={loading}
      loadingLabel="در حال دریافت جزئیات راننده"
      error={error}
      onRetry={() => driverId && void loadDriver(driverId)}
      emptyTitle="راننده یافت نشد"
      activeTab={tab}
      onTabChange={setTab}
    />
  );
}

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  Drawer,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  Close,
  DirectionsCar,
  Error as ErrorIcon,
  Inbox,
  Speed,
  Search,
  Sync,
  TaskAlt,
} from '@mui/icons-material';
import { api, ApiError } from '../../api/client';
import { KpiCard } from '../../components/KpiCard';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { PageHeader } from '../../components/PageHeader';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlTextField } from '../../components/RtlTextField';
import type { Fault, OdometerReading, RepairOrder, Vehicle, VehicleStatus, VehicleSummary } from '../../types/fmms';
import { formatDate, formatDateTime, toFaNumber } from '../../utils/format';

const statusOptions: Array<{ value: '' | VehicleStatus; label: string }> = [
  { value: '', label: 'همه وضعیت‌ها' },
  { value: 'ACTIVE', label: 'عملیاتی' },
  { value: 'UNDER_REPAIR', label: 'در تعمیر' },
  { value: 'WAITING_DRIVER_CONFIRMATION', label: 'منتظر تایید راننده' },
  { value: 'OUT_OF_SERVICE', label: 'خارج از سرویس' },
  { value: 'SUSPENDED', label: 'تعلیق‌شده' },
  { value: 'INACTIVE', label: 'غیرفعال' },
  { value: 'DECOMMISSIONED', label: 'از رده خارج' },
];

function useVehicleSummary() {
  const [summary, setSummary] = useState<VehicleSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      setSummary(await api.getVehicleSummary());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در دریافت خلاصه خودروها');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  return { summary, loading, error, reload: load };
}

function useVehicles(status: '' | VehicleStatus, ordering: string) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.listVehicles(status, ordering);
      setVehicles(result.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در دریافت خودروها');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, [status, ordering]);
  return { vehicles, loading, error, reload: load };
}

function driverName(driver: Vehicle['driver1']): string {
  if (!driver) return '—';
  return driver.name || driver.customer_number;
}

function VehicleCard({ vehicle, onOpen }: { vehicle: Vehicle; onOpen: (vehicle: Vehicle) => void }) {
  return (
    <Card onClick={() => onOpen(vehicle)} sx={{ cursor: 'pointer' }}>
      <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
        <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
          <Box minWidth={0}>
            <Typography fontWeight={900} noWrap>
              {vehicle.license_plate}
            </Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              شناسه خودرو: {vehicle.vehicle_number}
            </Typography>
          </Box>
          <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />
        </Stack>
        <Divider sx={{ my: 1.25 }} />
        <Grid container spacing={1}>
          <Grid size={6}>
            <Typography variant="caption" color="text.secondary">راننده</Typography>
            <Typography variant="body2" noWrap>{driverName(vehicle.driver1)}</Typography>
          </Grid>
          <Grid size={6}>
            <Typography variant="caption" color="text.secondary">کمک راننده</Typography>
            <Typography variant="body2" noWrap>{driverName(vehicle.driver2)}</Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

type VehicleSortKey = 'license_plate' | 'vehicle_number' | 'status';
type VehicleColumnKey = VehicleSortKey | 'driver1' | 'driver2' | 'actions';

function VehicleTable({
  vehicles,
  onOpen,
  orderBy,
  order,
  onSort,
}: {
  vehicles: Vehicle[];
  onOpen: (vehicle: Vehicle) => void;
  orderBy: VehicleSortKey;
  order: 'asc' | 'desc';
  onSort: (key: VehicleSortKey) => void;
}) {
  const columns: Array<RtlDataTableColumn<Vehicle, VehicleColumnKey>> = [
    {
      key: 'license_plate',
      label: 'پلاک',
      sortable: true,
      render: (vehicle) => <Typography fontWeight={800}>{vehicle.license_plate}</Typography>,
    },
    { key: 'vehicle_number', label: 'ای دی خودرو', sortable: true, render: (vehicle) => vehicle.vehicle_number },
    {
      key: 'status',
      label: 'وضعیت',
      sortable: true,
      render: (vehicle) => <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />,
    },
    { key: 'driver1', label: 'راننده', render: (vehicle) => driverName(vehicle.driver1) },
    { key: 'driver2', label: 'کمک راننده', render: (vehicle) => driverName(vehicle.driver2) },
    {
      key: 'actions',
      label: 'اقدام',
      align: 'center',
      render: (vehicle) => <Button size="small" onClick={() => onOpen(vehicle)}>جزئیات</Button>,
    },
  ];

  return (
    <RtlDataTable
      columns={columns}
      rows={vehicles}
      getRowKey={(vehicle) => vehicle.id}
      minWidth={880}
      orderBy={orderBy}
      order={order}
      onSort={(key) => {
        if (key !== 'actions' && key !== 'driver1' && key !== 'driver2') onSort(key);
      }}
    />
  );
}

function DetailLine({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" gap={2} py={1}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Box textAlign="left" minWidth={0}>{value}</Box>
    </Stack>
  );
}

function OdometerForm({ vehicle, onSaved }: { vehicle: Vehicle; onSaved: () => void }) {
  const today = new Date().toISOString().slice(0, 10);
  const [readingDate, setReadingDate] = useState(today);
  const [odometerKm, setOdometerKm] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setError('');
    setSaving(true);
    try {
      await api.recordOdometer(vehicle.id, {
        reading_date: readingDate,
        odometer_km: Number(odometerKm),
      });
      setOdometerKm('');
      onSaved();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError('ثبت کیلومتر انجام نشد');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h3" mb={2}>ثبت کیلومتر روزانه</Typography>
        <Stack spacing={1.5}>
          {error && <Alert severity="error">{error}</Alert>}
          <RtlTextField
            label="تاریخ"
            type="date"
            value={readingDate}
            onChange={(event) => setReadingDate(event.target.value)}
            InputLabelProps={{ shrink: true }}
            fullWidth
          />
          <RtlTextField
            label="کیلومتر"
            type="number"
            value={odometerKm}
            onChange={(event) => setOdometerKm(event.target.value)}
            fullWidth
          />
          <Button variant="contained" disabled={!odometerKm || saving} onClick={submit}>
            ثبت
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

function VehicleDetailDrawer({
  vehicle,
  open,
  onClose,
}: {
  vehicle: Vehicle | null;
  open: boolean;
  onClose: () => void;
}) {
  const [detail, setDetail] = useState<Vehicle | null>(null);
  const [odometer, setOdometer] = useState<OdometerReading[]>([]);
  const [faults, setFaults] = useState<Fault[]>([]);
  const [repairs, setRepairs] = useState<RepairOrder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadDetail = async () => {
    if (!vehicle) return;
    setLoading(true);
    setError('');
    try {
      const [vehicleDetail, odo, vehicleFaults, vehicleRepairs] = await Promise.all([
        api.getVehicle(vehicle.id),
        api.getOdometerHistory(vehicle.id),
        api.listFaults(vehicle.id),
        api.listRepairOrders(vehicle.id),
      ]);
      setDetail(vehicleDetail);
      setOdometer(odo);
      setFaults(vehicleFaults.results);
      setRepairs(vehicleRepairs.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در دریافت جزئیات خودرو');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setDetail(null);
    if (open) void loadDetail();
  }, [open, vehicle?.id]);

  const displayVehicle = detail ?? vehicle;
  const latestOdometer = odometer[0];
  const usedParts = repairs.flatMap((repair) => repair.parts ?? []);

  return (
    <Drawer anchor="left" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 520 } } }}>
      {displayVehicle && (
        <Box p={{ xs: 2, sm: 2.5 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2} mb={2}>
            <Box minWidth={0}>
              <Typography variant="h2">جزئیات خودرو</Typography>
              <Typography color="text.secondary" noWrap>
                {displayVehicle.license_plate} · {displayVehicle.vehicle_number}
              </Typography>
            </Box>
            <IconButton onClick={onClose}><Close /></IconButton>
          </Stack>

          {loading && <LoadingState />}
          {error && <ErrorState message={error} onRetry={loadDetail} />}
          {!loading && !error && (
            <Stack spacing={2}>
              <Card>
                <CardContent>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                    <Typography variant="h3">اطلاعات پایه</Typography>
                    <VehicleStatusBadge status={displayVehicle.status} label={displayVehicle.status_label} />
                  </Stack>
                  <DetailLine label="پلاک" value={<Typography fontWeight={800}>{displayVehicle.license_plate}</Typography>} />
                  <DetailLine label="ای دی خودرو" value={<Typography variant="body2">{displayVehicle.vehicle_number}</Typography>} />
                  <DetailLine label="راننده" value={<Typography variant="body2">{driverName(displayVehicle.driver1)}</Typography>} />
                  <DetailLine label="کمک راننده" value={<Typography variant="body2">{driverName(displayVehicle.driver2)}</Typography>} />
                  <DetailLine label="تاریخ بهره‌برداری" value={displayVehicle.commissioning_date || '—'} />
                  <DetailLine label="آخرین کیلومتر" value={latestOdometer ? `${toFaNumber(latestOdometer.odometer_km)} km` : '—'} />
                </CardContent>
              </Card>

              <OdometerForm vehicle={displayVehicle} onSaved={loadDetail} />

              <Card>
                <CardContent>
                  <Typography variant="h3" mb={1.5}>تاریخچه کیلومتر</Typography>
                  {odometer.length ? (
                    <Stack divider={<Divider />} spacing={0}>
                      {odometer.slice(0, 8).map((item) => (
                        <DetailLine
                          key={item.id}
                          label={formatDate(item.reading_date)}
                          value={`${toFaNumber(item.odometer_km)} km`}
                        />
                      ))}
                    </Stack>
                  ) : <EmptyState title="رکورد کیلومتری ثبت نشده است" />}
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <Typography variant="h3" mb={1.5}>خرابی‌های خودرو</Typography>
                  {faults.length ? (
                    <Stack spacing={1}>
                      {faults.slice(0, 8).map((fault) => (
                        <Box key={fault.id} p={1.25} border="1px solid" borderColor="divider" borderRadius={1}>
                          <Stack direction="row" justifyContent="space-between" gap={1}>
                            <Typography fontWeight={800}>{fault.description}</Typography>
                            <PlainStatusBadge label={fault.status} />
                          </Stack>
                          <Typography variant="caption" color="text.secondary">
                            {fault.code} · {formatDateTime(fault.reported_at || fault.created_at)}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  ) : <EmptyState title="خرابی ثبت نشده است" />}
                </CardContent>
              </Card>

              <Card>
                <CardContent>
                  <Typography variant="h3" mb={1.5}>تعمیرات و قطعات مصرفی</Typography>
                  {repairs.length ? (
                    <Stack spacing={1}>
                      {repairs.slice(0, 6).map((repair) => (
                        <Box key={repair.id} p={1.25} border="1px solid" borderColor="divider" borderRadius={1}>
                          <Stack direction="row" justifyContent="space-between" gap={1}>
                            <Typography fontWeight={800}>دستور تعمیر {repair.id.slice(0, 8)}</Typography>
                            <PlainStatusBadge label={repair.status} />
                          </Stack>
                          <Typography variant="caption" color="text.secondary">
                            تعمیرگاه: {repair.workshop_type || '—'} · {formatDateTime(repair.updated_at)}
                          </Typography>
                        </Box>
                      ))}
                      <Divider />
                      <Typography variant="body2" color="text.secondary">
                        قطعات مصرف‌شده: {usedParts.length ? `${toFaNumber(usedParts.length)} قلم` : '—'}
                      </Typography>
                    </Stack>
                  ) : <EmptyState title="سابقه تعمیر ثبت نشده است" />}
                </CardContent>
              </Card>
            </Stack>
          )}
        </Box>
      )}
    </Drawer>
  );
}

export function VehiclePage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [status, setStatus] = useState<'' | VehicleStatus>('');
  const [orderBy, setOrderBy] = useState<VehicleSortKey>('license_plate');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Vehicle | null>(null);
  const ordering = `${order === 'desc' ? '-' : ''}${orderBy}`;
  const { summary, loading: summaryLoading, error: summaryError, reload: reloadSummary } = useVehicleSummary();
  const { vehicles, loading, error, reload } = useVehicles(status, ordering);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return vehicles;
    return vehicles.filter((vehicle) =>
      [
        vehicle.license_plate,
        vehicle.vehicle_number,
        vehicle.status_label,
        vehicle.driver1?.customer_number,
        vehicle.driver1?.name,
        vehicle.driver2?.customer_number,
        vehicle.driver2?.name,
      ]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(needle),
    );
  }, [query, vehicles]);

  const changeSort = (key: VehicleSortKey) => {
    if (orderBy === key) {
      setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setOrderBy(key);
    setOrder('asc');
  };

  return (
    <Stack spacing={{ xs: 1.5, md: 2.25 }} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="خودروها"
        breadcrumbs={[
          { label: 'مدیریت ناوگان', to: '/vehicles' },
          { label: 'خودروها' },
        ]}
      />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(2, minmax(0, 1fr))',
            md: 'repeat(3, minmax(0, 1fr))',
            xl: 'repeat(6, minmax(0, 1fr))',
          },
          gap: 1.5,
        }}
      >
        <KpiCard label="کل ناوگان فعال" value={summaryLoading ? '...' : toFaNumber(summary?.active_fleet_count)} icon={DirectionsCar} />
        <KpiCard label="عملیاتی" value={summaryLoading ? '...' : toFaNumber(summary?.operational_fleet_count)} icon={TaskAlt} tone="success" />
        <KpiCard label="در تعمیر" value={summaryLoading ? '...' : toFaNumber(summary?.under_repair_fleet_count)} icon={Speed} tone="warning" />
        <KpiCard label="میانگین کیلومتر" value={summaryLoading ? '...' : toFaNumber(summary?.average_odometer_km)} icon={Speed} tone="info" />
        <KpiCard label="میانگین خرابی ماه" value={summaryLoading ? '...' : toFaNumber(summary?.average_faults_last_30_days)} icon={ErrorIcon} tone="warning" />
        <KpiCard
          label="آخرین همگام‌سازی SAP"
          value={summaryLoading ? '...' : formatDateTime(summary?.last_sap_sync_at)}
          icon={Sync}
          tone="info"
        />
      </Box>
      {summaryError && <ErrorState message={summaryError} onRetry={reloadSummary} />}

      <Card>
        <CardContent sx={{ p: { xs: 1.5, md: 2 }, '&:last-child': { pb: { xs: 1.5, md: 2 } } }}>
          <Stack
            direction={{ xs: 'column', md: 'row' }}
            spacing={{ xs: 1.5, md: 2 }}
            alignItems={{ xs: 'stretch', md: 'center' }}
            sx={{ direction: 'rtl' }}
          >
            <RtlTextField
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="جستجو بر اساس پلاک، ای دی خودرو یا نام راننده"
              fullWidth
              InputProps={{ endAdornment: <InputAdornment position="end"><Search /></InputAdornment> }}
            />
            <FormControl sx={{ minWidth: { xs: '100%', md: 220 }, direction: 'rtl' }}>
              <InputLabel id="vehicle-status-filter-label">وضعیت</InputLabel>
              <Select
                labelId="vehicle-status-filter-label"
                value={status}
                label="وضعیت"
                onChange={(event) => setStatus(event.target.value as '' | VehicleStatus)}
              >
                {statusOptions.map((item) => (
                  <MenuItem key={item.value || 'all'} value={item.value}>{item.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
        </CardContent>
      </Card>

      {loading && <LoadingState />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {!loading && !error && filtered.length === 0 && <EmptyState title="خودرویی یافت نشد" icon={Inbox} />}
      {!loading && !error && filtered.length > 0 && (
        isMobile ? (
          <Stack spacing={1}>
            {filtered.map((vehicle) => <VehicleCard key={vehicle.id} vehicle={vehicle} onOpen={setSelected} />)}
          </Stack>
        ) : (
          <VehicleTable
            vehicles={filtered}
            onOpen={setSelected}
            orderBy={orderBy}
            order={order}
            onSort={changeSort}
          />
        )
      )}

      <VehicleDetailDrawer
        vehicle={selected}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
      />
    </Stack>
  );
}

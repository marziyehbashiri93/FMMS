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
import type { Fault, OdometerReading, RepairOrder, Vehicle, VehicleStatus } from '../../types/fmms';
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

function useVehicles(status: '' | VehicleStatus) {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.listVehicles(status);
      setVehicles(result.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'خطا در دریافت خودروها');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, [status]);
  return { vehicles, loading, error, reload: load };
}

function VehicleCard({ vehicle, onOpen }: { vehicle: Vehicle; onOpen: (vehicle: Vehicle) => void }) {
  return (
    <Card onClick={() => onOpen(vehicle)} sx={{ cursor: 'pointer' }}>
      <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
        <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
          <Box minWidth={0}>
            <Typography fontWeight={900} noWrap>
              {vehicle.plate_number}
            </Typography>
            <Typography variant="body2" color="text.secondary" noWrap>
              {vehicle.make} {vehicle.model} · {toFaNumber(vehicle.year)}
            </Typography>
          </Box>
          <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />
        </Stack>
        <Divider sx={{ my: 1.25 }} />
        <Grid container spacing={1}>
          <Grid size={6}>
            <Typography variant="caption" color="text.secondary">VIN</Typography>
            <Typography variant="body2" noWrap>{vehicle.vin}</Typography>
          </Grid>
          <Grid size={6}>
            <Typography variant="caption" color="text.secondary">SAP</Typography>
            <Typography variant="body2" noWrap>{vehicle.sap_equipment_number || '—'}</Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
}

type VehicleSortKey = 'plate_number' | 'vin' | 'model' | 'year' | 'status' | 'sap_equipment_number';
type VehicleColumnKey = VehicleSortKey | 'actions';

function getVehicleSortValue(vehicle: Vehicle, key: VehicleSortKey) {
  if (key === 'model') return `${vehicle.make} ${vehicle.model}`;
  return vehicle[key] ?? '';
}

function VehicleTable({ vehicles, onOpen }: { vehicles: Vehicle[]; onOpen: (vehicle: Vehicle) => void }) {
  const [orderBy, setOrderBy] = useState<VehicleSortKey>('plate_number');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const sortedVehicles = useMemo(() => {
    return [...vehicles].sort((a, b) => {
      const aValue = getVehicleSortValue(a, orderBy);
      const bValue = getVehicleSortValue(b, orderBy);
      const result = String(aValue).localeCompare(String(bValue), 'fa', { numeric: true, sensitivity: 'base' });
      return order === 'asc' ? result : -result;
    });
  }, [order, orderBy, vehicles]);

  const changeSort = (key: VehicleSortKey) => {
    if (orderBy === key) {
      setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setOrderBy(key);
    setOrder('asc');
  };

  const columns: Array<RtlDataTableColumn<Vehicle, VehicleColumnKey>> = [
    {
      key: 'plate_number',
      label: 'پلاک',
      sortable: true,
      render: (vehicle) => <Typography fontWeight={800}>{vehicle.plate_number}</Typography>,
    },
    { key: 'vin', label: 'VIN', sortable: true, render: (vehicle) => vehicle.vin },
    { key: 'model', label: 'مدل', sortable: true, render: (vehicle) => `${vehicle.make} ${vehicle.model}` },
    { key: 'year', label: 'سال', sortable: true, render: (vehicle) => toFaNumber(vehicle.year) },
    {
      key: 'status',
      label: 'وضعیت',
      sortable: true,
      render: (vehicle) => <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />,
    },
    { key: 'sap_equipment_number', label: 'SAP Equipment', sortable: true, render: (vehicle) => vehicle.sap_equipment_number || '—' },
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
      rows={sortedVehicles}
      getRowKey={(vehicle) => vehicle.id}
      minWidth={880}
      orderBy={orderBy}
      order={order}
      onSort={(key) => {
        if (key !== 'actions') changeSort(key);
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
      const [odo, vehicleFaults, vehicleRepairs] = await Promise.all([
        api.getOdometerHistory(vehicle.id),
        api.listFaults(vehicle.id),
        api.listRepairOrders(vehicle.id),
      ]);
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
    if (open) void loadDetail();
  }, [open, vehicle?.id]);

  const latestOdometer = odometer[0];
  const usedParts = repairs.flatMap((repair) => repair.parts ?? []);

  return (
    <Drawer anchor="left" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 520 } } }}>
      {vehicle && (
        <Box p={{ xs: 2, sm: 2.5 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2} mb={2}>
            <Box minWidth={0}>
              <Typography variant="h2">جزئیات خودرو</Typography>
              <Typography color="text.secondary" noWrap>
                {vehicle.plate_number} · {vehicle.make} {vehicle.model}
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
                    <VehicleStatusBadge status={vehicle.status} label={vehicle.status_label} />
                  </Stack>
                  <DetailLine label="پلاک" value={<Typography fontWeight={800}>{vehicle.plate_number}</Typography>} />
                  <DetailLine label="VIN" value={<Typography variant="body2">{vehicle.vin}</Typography>} />
                  <DetailLine label="کد تجهیز SAP" value={<Typography variant="body2">{vehicle.sap_equipment_number || '—'}</Typography>} />
                  <DetailLine label="سال ساخت" value={toFaNumber(vehicle.year)} />
                  <DetailLine label="آخرین کیلومتر" value={latestOdometer ? `${toFaNumber(latestOdometer.odometer_km)} km` : '—'} />
                </CardContent>
              </Card>

              <OdometerForm vehicle={vehicle} onSaved={loadDetail} />

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
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Vehicle | null>(null);
  const { vehicles, loading, error, reload } = useVehicles(status);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return vehicles;
    return vehicles.filter((vehicle) =>
      [vehicle.plate_number, vehicle.vin, vehicle.make, vehicle.model, vehicle.sap_equipment_number]
        .filter(Boolean)
        .join(' ')
        .toLowerCase()
        .includes(needle),
    );
  }, [query, vehicles]);

  const activeCount = vehicles.filter((vehicle) => vehicle.status === 'ACTIVE').length;
  const repairCount = vehicles.filter((vehicle) => vehicle.status === 'UNDER_REPAIR').length;
  const unavailableCount = vehicles.filter((vehicle) => ['OUT_OF_SERVICE', 'DECOMMISSIONED'].includes(vehicle.status)).length;

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
            xl: 'repeat(5, minmax(0, 1fr))',
          },
          gap: 1.5,
        }}
      >
        <KpiCard label="کل ناوگان" value={toFaNumber(vehicles.length)} icon={DirectionsCar} />
        <KpiCard label="عملیاتی" value={toFaNumber(activeCount)} icon={TaskAlt} tone="success" />
        <KpiCard label="در تعمیر" value={toFaNumber(repairCount)} icon={Speed} tone="warning" />
        <KpiCard label="غیرقابل استفاده" value={toFaNumber(unavailableCount)} icon={ErrorIcon} tone="error" />
        <KpiCard label="همگام‌سازی SAP" value="زمان‌بندی‌شده" helper="آخرین داده‌ها از SAP خوانده می‌شود" icon={Sync} tone="info" />
      </Box>

      <Card>
        <CardContent sx={{ p: { xs: 1.5, md: 2 }, '&:last-child': { pb: { xs: 1.5, md: 2 } } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.25} sx={{ direction: 'rtl' }}>
            <RtlTextField
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="جستجو بر اساس پلاک، VIN یا مدل"
              fullWidth
              InputProps={{ endAdornment: <InputAdornment position="end"><Search /></InputAdornment> }}
            />
            <FormControl sx={{ minWidth: { xs: '100%', md: 220 }, direction: 'rtl' }}>
              <Select value={status} onChange={(event) => setStatus(event.target.value as '' | VehicleStatus)}>
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
          <VehicleTable vehicles={filtered} onOpen={setSelected} />
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

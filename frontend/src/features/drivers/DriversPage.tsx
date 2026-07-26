import { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Divider,
  InputAdornment,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  PeopleAlt,
  PersonOff,
  Search,
  Sync,
} from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DriverStatusBadge } from '../../components/DriverStatusBadge';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState } from '../../components/States';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlPagination } from '../../components/RtlPagination';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { Driver, DriverStatus, DriverSummary } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';
import { DriverDetailModal } from './DriverDetailModal';

type DriverSortKey =
  | 'customer_number'
  | 'name'
  | 'mobile'
  | 'personnel_number'
  | 'status';

const statusOptions: Array<{ value: '' | DriverStatus; label: string }> = [
  { value: '', label: 'همه وضعیت‌ها' },
  { value: 'ACTIVE', label: 'فعال' },
  { value: 'DECOMMISSIONED', label: 'غیرفعال' },
];

type DriverRoleFilter = '' | 'DRIVER' | 'ASSISTANT';

const roleOptions: Array<{ value: DriverRoleFilter; label: string }> = [
  { value: '', label: 'همه نقش‌ها' },
  { value: 'DRIVER', label: 'راننده' },
  { value: 'ASSISTANT', label: 'کمک راننده' },
];

const PAGE_SIZE = 20;

function vehiclePlate(vehicle: Driver['current_vehicle_as_driver']): string {
  if (!vehicle) return '—';
  return vehicle.license_plate || vehicle.vehicle_number || '—';
}

/** Merged current assignment: vehicle + role labels for table columns. */
function currentAssignment(driver: Driver): { vehicle: string; role: string } {
  const asDriver = driver.current_vehicle_as_driver;
  const asAssistant = driver.current_vehicle_as_assistant;

  if (asDriver && asAssistant) {
    return {
      vehicle: `${vehiclePlate(asDriver)} / ${vehiclePlate(asAssistant)}`,
      role: 'راننده / کمک راننده',
    };
  }
  if (asDriver) {
    return { vehicle: vehiclePlate(asDriver), role: 'راننده' };
  }
  if (asAssistant) {
    return { vehicle: vehiclePlate(asAssistant), role: 'کمک راننده' };
  }
  return { vehicle: '—', role: '—' };
}

/**
 * Driver management list page with KPIs, filters, and detail modal.
 */
export function DriversPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const navigate = useNavigate();
  const { driverId: routeDriverId } = useParams();

  const [summary, setSummary] = useState<DriverSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState('');

  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<'' | DriverStatus>('');
  const [role, setRole] = useState<DriverRoleFilter>('');
  const [orderBy, setOrderBy] = useState<DriverSortKey>('name');
  const [order, setOrder] = useState<'asc' | 'desc'>('asc');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(routeDriverId ?? null);

  const ordering = `${order === 'desc' ? '-' : ''}${orderBy}`;

  const loadSummary = async () => {
    setSummaryLoading(true);
    setSummaryError('');
    try {
      setSummary(await api.getDriverSummary());
    } catch (err) {
      setSummaryError(err instanceof Error ? err.message : 'خطا در دریافت خلاصه راننده‌ها');
    } finally {
      setSummaryLoading(false);
    }
  };

  const loadDrivers = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await api.listDrivers({
        status: status || undefined,
        ordering,
        search: search || undefined,
        role: role || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      setDrivers(result.results);
      setTotal(result.count);
    } catch (err) {
      setDrivers([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : 'خطا در دریافت راننده‌ها');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadSummary();
  }, []);

  useEffect(() => {
    void loadDrivers();
  }, [status, role, ordering, search, page]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = searchInput.trim();
      setSearch((prev) => {
        if (prev === next) return prev;
        setPage(1);
        return next;
      });
    }, 400);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (routeDriverId) setSelectedId(routeDriverId);
  }, [routeDriverId]);

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const openDriver = (id: string) => {
    setSelectedId(id);
    navigate(`/drivers/${id}`, { replace: true });
  };

  const closeDriver = () => {
    setSelectedId(null);
    navigate('/drivers', { replace: true });
  };

  const columns: Array<
    RtlDataTableColumn<Driver, DriverSortKey | 'vehicle' | 'role' | 'details'>
  > = [
    { key: 'customer_number', label: 'شناسه راننده', sortable: true },
    { key: 'name', label: 'نام راننده', sortable: true },
    {
      key: 'mobile',
      label: 'موبایل',
      sortable: true,
      render: (row) => row.mobile || '—',
    },
    {
      key: 'personnel_number',
      label: 'شماره پرسنلی',
      sortable: true,
      render: (row) => row.personnel_number || '—',
    },
    {
      key: 'status',
      label: 'وضعیت',
      sortable: true,
      skeleton: 'badge',
      render: (row) => <DriverStatusBadge status={row.status} />,
    },
    {
      key: 'vehicle',
      label: 'خودرو',
      render: (row) => currentAssignment(row).vehicle,
    },
    {
      key: 'role',
      label: 'نقش',
      render: (row) => currentAssignment(row).role,
    },
    {
      key: 'details',
      label: 'جزئیات',
      align: 'center',
      skeleton: 'button',
      render: (row) => (
        <Button size="small" variant="outlined" onClick={() => openDriver(row.id)}>
          مشاهده
        </Button>
      ),
    },
  ];

  const resetFilters = () => {
    setSearchInput('');
    setSearch('');
    setStatus('');
    setRole('');
    setOrderBy('name');
    setOrder('asc');
    setPage(1);
  };

  const hasActiveFilters =
    search !== '' ||
    status !== '' ||
    role !== '' ||
    orderBy !== 'name' ||
    order !== 'asc' ||
    page !== 1;

  return (
    <FeaturePage>
      <PageHeader
        title="راننده‌ها"
        breadcrumbs={[
          { label: 'راننده' },
          { label: 'لیست راننده‌ها' },
        ]}
      />

      <KpiGrid>
        <KpiCard
          label="راننده‌های فعال"
          value={summaryLoading ? '...' : toFaNumber(summary?.active_count)}
          icon={PeopleAlt}
        />
        <KpiCard
          label="راننده‌های غیرفعال"
          value={summaryLoading ? '...' : toFaNumber(summary?.decommissioned_count)}
          icon={PersonOff}
          tone="error"
        />
        <KpiCard
          label="آخرین همگام‌سازی SAP"
          value={summaryLoading ? '...' : formatDateTime(summary?.last_sap_sync_at)}
          icon={Sync}
          tone="info"
        />
      </KpiGrid>
      {summaryError && <ErrorState message={summaryError} onRetry={loadSummary} />}

      <FilterPanel>
        <RtlTextField
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          label="جستجو"
          placeholder="نام راننده یا شماره پرسنلی"
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ width: { xs: '100%', md: 280 }, flexShrink: 0 }}
        />
        <RtlSelectField<'' | DriverStatus>
          value={status}
          label="وضعیت"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value as '' | DriverStatus);
          }}
          renderValue={(selected) => {
            if (!selected) return <PlainStatusBadge label="همه وضعیت‌ها" />;
            const option = statusOptions.find((item) => item.value === selected);
            return <DriverStatusBadge status={String(selected)} label={option?.label} />;
          }}
          sx={{ width: { xs: '100%', md: 200 }, flexShrink: 0 }}
        >
          {statusOptions.map((item) => (
            <MenuItem key={item.value || 'all'} value={item.value}>
              {item.value ? (
                <DriverStatusBadge status={item.value} label={item.label} />
              ) : (
                <PlainStatusBadge label={item.label} />
              )}
            </MenuItem>
          ))}
        </RtlSelectField>
        <RtlSelectField<DriverRoleFilter>
          value={role}
          label="نقش"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => {
            setPage(1);
            setRole(event.target.value as DriverRoleFilter);
          }}
          renderValue={(selected) => {
            const option = roleOptions.find((item) => item.value === selected);
            return <PlainStatusBadge label={option?.label ?? 'همه نقش‌ها'} />;
          }}
          sx={{ width: { xs: '100%', md: 180 }, flexShrink: 0 }}
        >
          {roleOptions.map((item) => (
            <MenuItem key={item.value || 'all-roles'} value={item.value}>
              <PlainStatusBadge label={item.label} />
            </MenuItem>
          ))}
        </RtlSelectField>
        <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
      </FilterPanel>

      {error && <ErrorState message={error} onRetry={loadDrivers} />}

      {!error && !isMobile && (
        <RtlDataTable
          columns={columns}
          rows={drivers}
          getRowKey={(row) => row.id}
          loading={loading}
          orderBy={orderBy}
          order={order}
          onSort={(key) => {
            if (key === 'vehicle' || key === 'role' || key === 'details') return;
            const sortKey = key as DriverSortKey;
            setPage(1);
            if (orderBy === sortKey) {
              setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
              return;
            }
            setOrderBy(sortKey);
            setOrder('asc');
          }}
          emptyMessage="راننده‌ای یافت نشد"
          emptySubtitle="با تغییر فیلترها دوباره تلاش کنید"
          minWidth={980}
        />
      )}

      {!error && isMobile && (
        <Stack spacing={1.25}>
          {loading &&
            Array.from({ length: 4 }).map((_, index) => (
              <Card key={index}>
                <CardContent sx={{ p: 1.75 }}>
                  <Typography color="text.secondary">در حال بارگذاری...</Typography>
                </CardContent>
              </Card>
            ))}
          {!loading && drivers.length === 0 && (
            <EmptyState title="راننده‌ای یافت نشد" subtitle="با تغییر فیلترها دوباره تلاش کنید" />
          )}
          {!loading &&
            drivers.map((driver) => {
              const assignment = currentAssignment(driver);
              return (
                <Card key={driver.id} onClick={() => openDriver(driver.id)} sx={{ cursor: 'pointer' }}>
                  <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                    <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
                      <Box minWidth={0}>
                        <Typography fontWeight={900} noWrap>
                          {driver.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" noWrap>
                          {driver.customer_number}
                        </Typography>
                      </Box>
                      <DriverStatusBadge status={driver.status} />
                    </Stack>
                    <Divider sx={{ my: 1.25 }} />
                    <Typography variant="body2" color="text.secondary">
                      موبایل: {driver.mobile || '—'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      خودرو: {assignment.vehicle}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      نقش: {assignment.role}
                    </Typography>
                  </CardContent>
                </Card>
              );
            })}
        </Stack>
      )}

      {!error && (
        <RtlPagination
          page={page}
          count={pageCount}
          onChange={setPage}
          totalItems={total}
          pageSize={PAGE_SIZE}
          disabled={loading}
        />
      )}

      <DriverDetailModal open={Boolean(selectedId)} driverId={selectedId} onClose={closeDriver} />
    </FeaturePage>
  );
}

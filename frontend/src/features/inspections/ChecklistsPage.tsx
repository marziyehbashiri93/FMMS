import { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Link,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { Close, FactCheck, Inbox } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { JalaliDateRangeFilter } from '../../components/JalaliDateRangeFilter';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlPagination } from '../../components/RtlPagination';
import { RtlSelectField } from '../../components/RtlSelectField';
import type { Inspection, Vehicle } from '../../types/fmms';
import { isValidIsoDateRange } from '../../utils/dateRange';
import { formatDateTime, toFaNumber } from '../../utils/format';
import {
  checklistOverallLabel,
  checklistOverallTone,
  sortChecklistItems,
} from './checklistDisplay';

const PAGE_SIZE = 20;

const INSPECTION_TYPE_LABELS: Record<string, string> = {
  PRE_TRIP: 'پیش از حرکت',
  POST_TRIP: 'پس از حرکت',
  PERIODIC: 'دوره‌ای',
  UNSCHEDULED: 'خارج از برنامه',
};

const INSPECTION_STATUS_LABELS: Record<string, string> = {
  DRAFT: 'پیش‌نویس',
  SUBMITTED: 'ثبت‌شده',
  REVIEWED: 'بررسی‌شده',
};

const CHECKLIST_RESULT_LABELS: Record<string, string> = {
  PASS: 'قبول',
  FAIL: 'مردود',
  NOT_APPLICABLE: 'نامرتبط',
  NA: 'نامرتبط',
};

const SEVERITY_LABELS: Record<string, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

type ChecklistSortKey =
  | 'inspected_at'
  | 'inspection_type'
  | 'odometer_value'
  | 'status'
  | 'overall_result';

function normalizeInspections(payload: { results?: Inspection[]; count?: number } | Inspection[]): {
  items: Inspection[];
  total: number;
} {
  if (Array.isArray(payload)) {
    return { items: payload, total: payload.length };
  }
  const items = payload.results ?? [];
  return { items, total: payload.count ?? items.length };
}

function vehicleLabel(vehicle: Vehicle | undefined, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

/**
 * Admin checklist history list under the vehicle navigation group.
 */
export function ChecklistsPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [checklists, setChecklists] = useState<Inspection[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [vehicleId, setVehicleId] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [page, setPage] = useState(1);
  const [orderBy, setOrderBy] = useState<ChecklistSortKey>('inspected_at');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selected, setSelected] = useState<Inspection | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const vehicleMap = useMemo(() => {
    const map = new Map<string, Vehicle>();
    vehicles.forEach((vehicle) => map.set(vehicle.id, vehicle));
    return map;
  }, [vehicles]);

  const loadVehicles = async () => {
    try {
      const result = await api.listVehicles('', '-created_at', { page: 1, pageSize: 100 });
      setVehicles(result.results ?? []);
    } catch {
      setVehicles([]);
    }
  };

  const loadChecklists = async () => {
    if (!isValidIsoDateRange(fromDate, toDate)) return;
    setLoading(true);
    setError('');
    try {
      const payload = await api.listInspections({
        vehicleId: vehicleId || undefined,
        fromDate: fromDate || undefined,
        toDate: toDate || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      const { items, total: count } = normalizeInspections(payload);
      setChecklists(items);
      setTotal(count);
    } catch (err) {
      setChecklists([]);
      setTotal(0);
      setError(err instanceof Error ? err.message : 'خطا در دریافت چک‌لیست‌ها');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadVehicles();
  }, []);

  useEffect(() => {
    void loadChecklists();
  }, [vehicleId, fromDate, toDate, page]);

  const openDetail = async (inspectionId: string) => {
    setSelectedId(inspectionId);
    setDetailLoading(true);
    setDetailError('');
    setSelected(null);
    try {
      setSelected(await api.getInspection(inspectionId));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'خطا در دریافت جزئیات چک‌لیست';
      setDetailError(
        message === 'Failed to fetch' ? 'ارتباط با سرور برقرار نشد. دوباره تلاش کنید.' : message,
      );
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelectedId(null);
    setSelected(null);
    setDetailError('');
  };

  const sorted = [...checklists].sort((a, b) => {
    const dir = order === 'asc' ? 1 : -1;
    if (orderBy === 'odometer_value') {
      return ((a.odometer_value ?? 0) - (b.odometer_value ?? 0)) * dir;
    }
    return String(a[orderBy] ?? '').localeCompare(String(b[orderBy] ?? ''), 'fa') * dir;
  });

  const resetFilters = () => {
    setVehicleId('');
    setFromDate('');
    setToDate('');
    setPage(1);
    setOrderBy('inspected_at');
    setOrder('desc');
  };

  const hasActiveFilters =
    vehicleId !== '' ||
    fromDate !== '' ||
    toDate !== '' ||
    orderBy !== 'inspected_at' ||
    order !== 'desc' ||
    page !== 1;

  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const columns: Array<RtlDataTableColumn<Inspection, ChecklistSortKey | 'vehicle' | 'actions'>> = [
    {
      key: 'inspected_at',
      label: 'تاریخ بازرسی',
      sortable: true,
      render: (row) => formatDateTime(row.inspected_at),
    },
    {
      key: 'vehicle',
      label: 'خودرو',
      render: (row) => (
        <Link
          component={RouterLink}
          to={`/vehicles?vehicleId=${row.vehicle_id}`}
          underline="hover"
          fontWeight={800}
        >
          {vehicleLabel(vehicleMap.get(row.vehicle_id), row.vehicle_id)}
        </Link>
      ),
    },
    {
      key: 'inspection_type',
      label: 'نوع',
      sortable: true,
      render: (row) => INSPECTION_TYPE_LABELS[row.inspection_type] ?? row.inspection_type,
    },
    {
      key: 'odometer_value',
      label: 'کیلومتر',
      sortable: true,
      render: (row) =>
        row.odometer_value != null ? toFaNumber(row.odometer_value) : '—',
    },
    {
      key: 'status',
      label: 'وضعیت',
      sortable: true,
      render: (row) => (
        <PlainStatusBadge label={INSPECTION_STATUS_LABELS[row.status] ?? row.status} />
      ),
    },
    {
      key: 'overall_result',
      label: 'نتیجه',
      sortable: true,
      render: (row) => (
        <PlainStatusBadge
          tone={checklistOverallTone(row.has_failures, row.overall_result)}
          label={checklistOverallLabel(row.has_failures, row.overall_result, CHECKLIST_RESULT_LABELS)}
        />
      ),
    },
    {
      key: 'actions',
      label: 'جزئیات',
      align: 'center',
      skeleton: 'button',
      render: (row) => (
        <Button size="small" variant="outlined" onClick={() => void openDetail(row.id)}>
          مشاهده
        </Button>
      ),
    },
  ];

  const itemColumns: Array<
    RtlDataTableColumn<Inspection['items'][number], 'category' | 'description' | 'result' | 'severity' | 'notes'>
  > = [
    { key: 'category', label: 'دسته', render: (row) => row.category || '—' },
    { key: 'description', label: 'شرح', render: (row) => row.description || '—' },
    {
      key: 'result',
      label: 'نتیجه',
      render: (row) => (
        <PlainStatusBadge
          tone={row.result === 'FAIL' ? 'error' : row.result === 'PASS' ? 'success' : 'neutral'}
          label={CHECKLIST_RESULT_LABELS[row.result] ?? row.result}
        />
      ),
    },
    {
      key: 'severity',
      label: 'شدت',
      render: (row) =>
        row.severity ? (
          <Typography fontWeight={row.result === 'FAIL' ? 800 : 500} color={row.result === 'FAIL' ? 'error.main' : 'inherit'}>
            {SEVERITY_LABELS[row.severity] ?? row.severity}
          </Typography>
        ) : (
          '—'
        ),
    },
    {
      key: 'notes',
      label: 'یادداشت',
      render: (row) =>
        row.notes ? (
          <Typography fontWeight={row.result === 'FAIL' ? 700 : 400}>{row.notes}</Typography>
        ) : (
          '—'
        ),
    },
  ];

  return (
    <FeaturePage>
      <PageHeader
        title="لیست بازرسی روزانه"
        breadcrumbs={[
          { label: 'خودرو' },
          { label: 'لیست بازرسی روزانه' },
        ]}
      />

      <FilterPanel>
        <RtlSelectField<string>
          value={vehicleId}
          label="خودرو"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => {
            setPage(1);
            setVehicleId(String(event.target.value));
          }}
          renderValue={(selected) => {
            if (!selected) return 'همه خودروها';
            const vehicle = vehicleMap.get(String(selected));
            return vehicleLabel(vehicle, String(selected));
          }}
          sx={{ width: { xs: '100%', md: 220 }, flexShrink: 0 }}
        >
          <MenuItem value="">همه خودروها</MenuItem>
          {vehicles.map((vehicle) => (
            <MenuItem key={vehicle.id} value={vehicle.id}>
              {vehicle.license_plate || vehicle.vehicle_number}
            </MenuItem>
          ))}
        </RtlSelectField>
        <JalaliDateRangeFilter
          fromDate={fromDate}
          toDate={toDate}
          showClear={false}
          onChange={({ fromDate: nextFrom, toDate: nextTo }) => {
            setPage(1);
            setFromDate(nextFrom);
            setToDate(nextTo);
          }}
        />
        <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
      </FilterPanel>

      {error && <ErrorState message={error} onRetry={loadChecklists} />}

      {!error && !isMobile && (
        <RtlDataTable
          columns={columns}
          rows={sorted}
          getRowKey={(row) => row.id}
          loading={loading}
          orderBy={orderBy}
          order={order}
          onSort={(key) => {
            if (key === 'vehicle' || key === 'actions') return;
            if (orderBy === key) {
              setOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
              return;
            }
            setOrderBy(key);
            setOrder('asc');
          }}
          emptyMessage="چک‌لیستی ثبت نشده است"
          emptySubtitle="با تغییر فیلترها دوباره تلاش کنید"
          emptyIcon={Inbox}
          minWidth={960}
        />
      )}

      {!error && isMobile && (
        <Stack spacing={1.25}>
          {loading && <LoadingState label="در حال دریافت چک‌لیست‌ها" />}
          {!loading && checklists.length === 0 && (
            <EmptyState title="چک‌لیستی ثبت نشده است" subtitle="با تغییر فیلترها دوباره تلاش کنید" icon={Inbox} />
          )}
          {!loading &&
            sorted.map((row) => (
              <Card key={row.id} onClick={() => void openDetail(row.id)} sx={{ cursor: 'pointer' }}>
                <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                  <Stack direction="row" justifyContent="space-between" gap={1.5} alignItems="flex-start">
                    <Box minWidth={0}>
                      <Typography fontWeight={900} noWrap>
                        {vehicleLabel(vehicleMap.get(row.vehicle_id), row.vehicle_id)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {formatDateTime(row.inspected_at)}
                      </Typography>
                    </Box>
                    <PlainStatusBadge
                      tone={checklistOverallTone(row.has_failures, row.overall_result)}
                      label={checklistOverallLabel(
                        row.has_failures,
                        row.overall_result,
                        CHECKLIST_RESULT_LABELS,
                      )}
                    />
                  </Stack>
                  <Divider sx={{ my: 1.25 }} />
                  <Typography variant="body2" color="text.secondary">
                    نوع: {INSPECTION_TYPE_LABELS[row.inspection_type] ?? row.inspection_type}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    وضعیت: {INSPECTION_STATUS_LABELS[row.status] ?? row.status}
                  </Typography>
                </CardContent>
              </Card>
            ))}
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

      <Dialog
        open={Boolean(selectedId)}
        onClose={closeDetail}
        fullWidth
        maxWidth="md"
        disableScrollLock
        dir="rtl"
        PaperProps={{
          sx: {
            borderRadius: (t) => t.radius('md'),
            height: { sm: 640, md: 680 },
            maxHeight: { sm: 640, md: 680 },
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            boxShadow: '0 24px 64px rgba(23, 35, 29, 0.18)',
          },
        }}
      >
        <DialogTitle sx={{ pr: 6, position: 'relative', flexShrink: 0 }}>
          <Stack direction="row" alignItems="center" gap={1}>
            <FactCheck fontSize="small" color="primary" />
            جزئیات چک‌لیست
          </Stack>
          <IconButton
            size="small"
            onClick={closeDetail}
            aria-label="بستن"
            sx={{ position: 'absolute', top: 12, left: 12 }}
          >
            <Close fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
          {detailLoading ? (
            <LoadingState label="در حال دریافت جزئیات چک‌لیست" />
          ) : detailError ? (
            <ErrorState
              message={detailError}
              onRetry={() => {
                if (selectedId) void openDetail(selectedId);
              }}
            />
          ) : selected ? (
            <Stack spacing={2}>
              <Box>
                <DetailLine label="تاریخ بازرسی" value={formatDateTime(selected.inspected_at)} />
                <DetailLine
                  label="خودرو"
                  value={
                    <Link
                      component={RouterLink}
                      to={`/vehicles?vehicleId=${selected.vehicle_id}`}
                      underline="hover"
                      fontWeight={800}
                      onClick={closeDetail}
                    >
                      {vehicleLabel(vehicleMap.get(selected.vehicle_id), selected.vehicle_id)}
                    </Link>
                  }
                />
                <DetailLine
                  label="نوع"
                  value={INSPECTION_TYPE_LABELS[selected.inspection_type] ?? selected.inspection_type}
                />
                <DetailLine
                  label="کیلومتر"
                  value={
                    selected.odometer_value != null
                      ? `${toFaNumber(selected.odometer_value)} ${
                          selected.odometer_unit === 'MILES' ? 'mi' : 'km'
                        }`
                      : '—'
                  }
                />
                <DetailLine
                  label="وضعیت"
                  value={
                    <PlainStatusBadge
                      label={INSPECTION_STATUS_LABELS[selected.status] ?? selected.status}
                    />
                  }
                />
                <DetailLine
                  label="نتیجه کلی"
                  value={
                    <PlainStatusBadge
                      tone={checklistOverallTone(selected.has_failures, selected.overall_result)}
                      label={checklistOverallLabel(
                        selected.has_failures,
                        selected.overall_result,
                        CHECKLIST_RESULT_LABELS,
                      )}
                    />
                  }
                />
                {selected.driver?.name && (
                  <DetailLine label="راننده" value={selected.driver.name} />
                )}
              </Box>
              <RtlDataTable
                columns={itemColumns}
                rows={sortChecklistItems(selected.items)}
                getRowKey={(row) => row.id}
                emptyMessage="آیتمی برای این چک‌لیست ثبت نشده است"
                standaloneEmpty
                minWidth={640}
              />
            </Stack>
          ) : null}
        </DialogContent>
      </Dialog>
    </FeaturePage>
  );
}

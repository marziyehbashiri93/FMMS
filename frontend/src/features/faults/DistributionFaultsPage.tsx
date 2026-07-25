import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
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
  CheckCircleOutline,
  DirectionsCar,
  DoNotDisturbAlt,
  FactCheck,
  ReportProblem,
  Search,
  WarningAmber,
} from '@mui/icons-material';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type { Fault, Inspection, Vehicle } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

const PAGE_SIZE = 50;

const FAULT_STATUS_LABELS: Record<string, string> = {
  OPEN: 'در انتظار تصمیم توزیع',
  AWAITING_TRANSPORT: 'تاییدشده توسط توزیع — صف ترابری',
  ASSIGNED: 'تخصیص‌یافته به تکنسین',
  IN_REPAIR: 'در تعمیر',
  CLOSED: 'بسته شده',
};

const SEVERITY_LABELS: Record<string, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

type DetailState = {
  fault: Fault;
  vehicle: Vehicle | null;
  checklists: Inspection[];
  faults: Fault[];
};

type FaultStatusFilter =
  | ''
  | 'OPEN'
  | 'AWAITING_TRANSPORT'
  | 'ASSIGNED'
  | 'IN_REPAIR'
  | 'CLOSED';

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function faultStatusLabel(status: string): string {
  return FAULT_STATUS_LABELS[status] ?? status;
}

function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity] ?? severity;
}

function severityTone(severity: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (severity === 'CRITICAL' || severity === 'HIGH') return 'error';
  if (severity === 'MEDIUM') return 'warning';
  if (severity === 'LOW') return 'neutral';
  return 'neutral';
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'CLOSED') return 'success';
  if (status === 'OPEN') return 'warning';
  if (status === 'AWAITING_TRANSPORT') return 'warning';
  if (status === 'ASSIGNED' || status === 'IN_REPAIR') return 'error';
  return 'neutral';
}

function vehiclePlate(vehicle: Vehicle | undefined, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

/**
 * Distribution unit queue for reviewing reported vehicle faults.
 */
export function DistributionFaultsPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [faults, setFaults] = useState<Fault[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<FaultStatusFilter>('');
  const [selected, setSelected] = useState<Fault | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [actionError, setActionError] = useState('');
  const [success, setSuccess] = useState('');
  const [decisionNote, setDecisionNote] = useState('');
  const [decisionLoading, setDecisionLoading] = useState<'usable' | 'unusable' | ''>('');

  const vehicleMap = useMemo(() => {
    const map = new Map<string, Vehicle>();
    vehicles.forEach((vehicle) => map.set(String(vehicle.id), vehicle));
    return map;
  }, [vehicles]);

  const loadFaults = async () => {
    setLoading(true);
    setError('');
    try {
      const faultPage = await api.listFaults(undefined, { page: 1, pageSize: PAGE_SIZE });
      const nextFaults = faultPage.results ?? [];
      setFaults(nextFaults);

      const vehicleIds = [...new Set(nextFaults.map((fault) => fault.vehicle_id).filter(Boolean))];
      const vehicleResults = await Promise.all(
        vehicleIds.map(async (id) => {
          try {
            return await api.getVehicle(id);
          } catch {
            return null;
          }
        }),
      );
      setVehicles(vehicleResults.filter((item): item is Vehicle => Boolean(item)));
    } catch (err) {
      setFaults([]);
      setVehicles([]);
      setError(err instanceof Error ? err.message : 'دریافت لیست خرابی‌ها انجام نشد');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadFaults();
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearch(searchInput.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const visibleFaults = useMemo(() => {
    const needle = search.toLowerCase();
    return faults.filter((fault) => {
      if (status && fault.status !== status) return false;
      if (!needle) return true;
      const vehicle = vehicleMap.get(String(fault.vehicle_id));
      return [
        fault.code,
        fault.description,
        fault.status,
        fault.severity,
        fault.sap_notification_number ?? '',
        vehicle?.license_plate ?? '',
        vehicle?.vehicle_number ?? '',
      ]
        .join(' ')
        .toLowerCase()
        .includes(needle);
    });
  }, [faults, search, status, vehicleMap]);

  const kpi = useMemo(() => {
    const openCount = faults.filter((item) => item.status === 'OPEN').length;
    const closedCount = faults.filter((item) => item.status === 'CLOSED').length;
    const criticalCount = faults.filter(
      (item) => item.severity === 'CRITICAL' || item.severity === 'HIGH',
    ).length;
    return {
      total: faults.length,
      openCount,
      closedCount,
      criticalCount,
    };
  }, [faults]);

  const openDetail = async (fault: Fault) => {
    setSelected(fault);
    setDecisionNote('');
    setDetail(null);
    setDetailError('');
    setActionError('');
    setDetailLoading(true);
    try {
      const [freshFault, vehicle, checklists, vehicleFaults] = await Promise.all([
        api.getFault(fault.id),
        api.getVehicle(fault.vehicle_id),
        api.listVehicleChecklists(fault.vehicle_id, { page: 1, pageSize: 20 }),
        api.listFaults(fault.vehicle_id, { page: 1, pageSize: 20 }),
      ]);
      setDetail({
        fault: freshFault,
        vehicle,
        checklists: normalizePaginated(checklists),
        faults: vehicleFaults.results ?? [],
      });
      setVehicles((current) => {
        if (current.some((item) => item.id === vehicle.id)) return current;
        return [...current, vehicle];
      });
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات خرابی انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelected(null);
    setDetail(null);
    setDetailError('');
    setActionError('');
    setDecisionNote('');
  };

  const decide = async (decision: 'usable' | 'unusable') => {
    const fault = detail?.fault ?? selected;
    if (!fault) return;
    setDecisionLoading(decision);
    setActionError('');
    setSuccess('');
    try {
      const updated =
        decision === 'usable'
          ? await api.markFaultVehicleUsable(fault.id, decisionNote)
          : await api.markFaultVehicleUnusable(fault.id, decisionNote);
      setFaults((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      closeDetail();
      setSuccess(
        decision === 'usable'
          ? 'خرابی بسته شد. راننده می‌تواند گرفتن خودرو و خروج از مرکز را تایید کند.'
          : 'خودرو خارج از سرویس شد و به صف ترابری ارسال شد.',
      );
      await loadFaults();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت تصمیم توزیع انجام نشد');
    } finally {
      setDecisionLoading('');
    }
  };

  const resetFilters = () => {
    setSearchInput('');
    setSearch('');
    setStatus('');
  };

  const hasActiveFilters = search !== '' || status !== '';
  const decisionDisabled = detail?.fault.status !== 'OPEN';

  const columns: Array<RtlDataTableColumn<Fault, string>> = [
    {
      key: 'plate',
      label: 'پلاک خودرو',
      minWidth: 140,
      render: (fault) => (
        <Typography fontWeight={800}>
          {vehiclePlate(vehicleMap.get(String(fault.vehicle_id)), fault.vehicle_id)}
        </Typography>
      ),
    },
    {
      key: 'description',
      label: 'شرح خرابی',
      minWidth: 220,
      render: (fault) => (
        <Stack spacing={0.35}>
          <Typography fontWeight={800}>{fault.description}</Typography>
          <Typography variant="caption" color="text.secondary">
            {fault.code} · {formatDateTime(fault.reported_at || fault.created_at)}
          </Typography>
        </Stack>
      ),
    },
    {
      key: 'severity',
      label: 'شدت',
      render: (fault) => (
        <PlainStatusBadge
          label={severityLabel(fault.severity)}
          tone={severityTone(fault.severity)}
        />
      ),
    },
    {
      key: 'sap',
      label: 'SAP',
      render: (fault) => (
        <Typography variant="body2" color="text.secondary">
          {fault.sap_notification_number || 'در صف ارسال'}
        </Typography>
      ),
    },
    {
      key: 'status',
      label: 'وضعیت',
      render: (fault) => (
        <PlainStatusBadge
          label={faultStatusLabel(fault.status)}
          tone={statusTone(fault.status)}
        />
      ),
    },
    {
      key: 'actions',
      label: 'عملیات',
      align: 'center',
      render: (fault) => (
        <Button
          size="small"
          variant="outlined"
          onClick={() => void openDetail(fault)}
          sx={{ height: 36, minHeight: 36, px: 1.5, minWidth: 72 }}
        >
          بررسی
        </Button>
      ),
    },
  ];

  const tabs = detail
    ? [
        {
          label: 'جزئیات خرابی',
          content: (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <DetailLine
                    label="پلاک"
                    value={vehiclePlate(detail.vehicle ?? undefined, detail.fault.vehicle_id)}
                  />
                  <DetailLine label="شرح" value={detail.fault.description} />
                  <DetailLine label="کد خرابی" value={detail.fault.code} />
                  <DetailLine label="شدت" value={severityLabel(detail.fault.severity)} />
                  <DetailLine label="وضعیت" value={faultStatusLabel(detail.fault.status)} />
                  <DetailLine
                    label="PM Notification"
                    value={detail.fault.sap_notification_number || 'در صف ارسال'}
                  />
                  <DetailLine
                    label="زمان ثبت"
                    value={formatDateTime(detail.fault.reported_at || detail.fault.created_at)}
                  />
                </CardContent>
              </Card>
              {decisionDisabled && (
                <Alert severity="info">
                  تصمیم توزیع برای این خرابی قبلا ثبت شده است.
                </Alert>
              )}
              {actionError && <Alert severity="error">{actionError}</Alert>}
              <RtlTextField
                fullWidth
                label="یادداشت تصمیم توزیع"
                value={decisionNote}
                onChange={(event) => setDecisionNote(event.target.value)}
              />
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1}
                justifyContent="flex-end"
                useFlexGap
              >
                <Button
                  color="success"
                  variant="contained"
                  size="small"
                  startIcon={<CheckCircleOutline />}
                  loading={decisionLoading === 'usable'}
                  disabled={decisionDisabled}
                  onClick={() => void decide('usable')}
                  sx={{
                    height: 40,
                    minHeight: 40,
                    px: 1.75,
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}
                >
                  خودرو قابل استفاده است
                </Button>
                <Button
                  color="error"
                  variant="contained"
                  size="small"
                  startIcon={<DoNotDisturbAlt />}
                  loading={decisionLoading === 'unusable'}
                  disabled={decisionDisabled}
                  onClick={() => void decide('unusable')}
                  sx={{
                    height: 40,
                    minHeight: 40,
                    px: 1.75,
                    whiteSpace: 'nowrap',
                    flexShrink: 0,
                  }}
                >
                  خودرو قابل استفاده نیست
                </Button>
              </Stack>
            </Stack>
          ),
        },
        {
          label: 'اطلاعات خودرو',
          content: detail.vehicle ? (
            <Card variant="outlined">
              <CardContent>
                <DetailLine label="پلاک" value={detail.vehicle.license_plate} />
                <DetailLine label="شماره خودرو" value={detail.vehicle.vehicle_number} />
                <DetailLine
                  label="وضعیت"
                  value={<VehicleStatusBadge status={detail.vehicle.status} />}
                />
                <DetailLine
                  label="راننده اصلی"
                  value={detail.vehicle.driver1?.name || detail.vehicle.driver1?.customer_number || '—'}
                />
                <DetailLine
                  label="کمک راننده"
                  value={detail.vehicle.driver2?.name || detail.vehicle.driver2?.customer_number || '—'}
                />
              </CardContent>
            </Card>
          ) : (
            <EmptyState title="اطلاعات خودرو در دسترس نیست" />
          ),
        },
        {
          label: 'چک‌لیست‌های روزانه',
          content: detail.checklists.length ? (
            <Stack spacing={1}>
              {detail.checklists.map((inspection) => (
                <Card key={inspection.id} variant="outlined">
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" gap={1}>
                      <Typography fontWeight={800}>
                        {formatDateTime(inspection.inspected_at)}
                      </Typography>
                      <PlainStatusBadge
                        label={
                          inspection.overall_result === 'PASS'
                            ? 'قبول'
                            : inspection.overall_result === 'FAIL'
                              ? 'مردود'
                              : inspection.overall_result
                        }
                        tone={inspection.overall_result === 'FAIL' ? 'error' : 'success'}
                      />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      کیلومتر: {toFaNumber(inspection.odometer_value)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      موارد ناموفق:{' '}
                      {toFaNumber(inspection.items.filter((item) => item.result === 'FAIL').length)}
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          ) : (
            <EmptyState title="چک‌لیستی برای این خودرو ثبت نشده است" icon={FactCheck} />
          ),
        },
        {
          label: 'تاریخچه خرابی‌ها',
          content: (() => {
            const historyFaults = detail.faults.filter((fault) => fault.id !== detail.fault.id);
            if (!historyFaults.length) {
              return <EmptyState title="خرابی قبلی برای این خودرو ثبت نشده است" />;
            }
            return (
              <Stack spacing={1}>
                {historyFaults.map((fault) => (
                  <Card key={fault.id} variant="outlined">
                    <CardContent>
                      <Typography fontWeight={800}>{fault.description}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {fault.code} · {faultStatusLabel(fault.status)} ·{' '}
                        {formatDateTime(fault.reported_at || fault.created_at)}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            );
          })(),
        },
      ]
    : [];

  return (
    <Stack spacing={{ xs: 1.5, md: 2.25 }} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="لیست خرابی‌ها"
        breadcrumbs={[{ label: 'توزیع خودرو' }, { label: 'لیست خرابی‌ها' }]}
      />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(2, minmax(0, 1fr))',
            md: 'repeat(4, minmax(0, 1fr))',
          },
          gap: 1.5,
        }}
      >
        <KpiCard
          label="کل خرابی‌ها"
          value={loading ? '...' : toFaNumber(kpi.total)}
          icon={ReportProblem}
        />
        <KpiCard
          label="در انتظار تصمیم"
          value={loading ? '...' : toFaNumber(kpi.openCount)}
          icon={WarningAmber}
          tone="warning"
        />
        <KpiCard
          label="شدت بالا / بحرانی"
          value={loading ? '...' : toFaNumber(kpi.criticalCount)}
          icon={ReportProblem}
          tone="error"
        />
        <KpiCard
          label="بسته شده"
          value={loading ? '...' : toFaNumber(kpi.closedCount)}
          icon={CheckCircleOutline}
          tone="success"
        />
      </Box>

      <FilterPanel>
        <RtlTextField
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          label="جستجو"
          placeholder="پلاک، شرح، کد یا SAP"
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search fontSize="small" />
              </InputAdornment>
            ),
          }}
          sx={{ width: { xs: '100%', md: 300 }, flexShrink: 0 }}
        />
        <RtlSelectField<FaultStatusFilter>
          value={status}
          label="وضعیت"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => setStatus(event.target.value as FaultStatusFilter)}
          renderValue={(selected) => {
            if (!selected) return <PlainStatusBadge label="همه وضعیت‌ها" />;
            return (
              <PlainStatusBadge
                label={faultStatusLabel(String(selected))}
                tone={statusTone(String(selected))}
              />
            );
          }}
          sx={{ width: { xs: '100%', md: 240 }, flexShrink: 0 }}
        >
          <MenuItem value="">
            <PlainStatusBadge label="همه وضعیت‌ها" />
          </MenuItem>
          {(Object.keys(FAULT_STATUS_LABELS) as Array<Exclude<FaultStatusFilter, ''>>).map(
            (value) => (
              <MenuItem key={value} value={value}>
                <PlainStatusBadge label={faultStatusLabel(value)} tone={statusTone(value)} />
              </MenuItem>
            ),
          )}
        </RtlSelectField>
        <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
      </FilterPanel>

      {success && <Alert severity="success">{success}</Alert>}
      {error && <ErrorState message={error} onRetry={() => void loadFaults()} />}

      {!error && !isMobile && (
        <RtlDataTable
          columns={columns}
          rows={visibleFaults}
          getRowKey={(fault) => fault.id}
          loading={loading}
          emptyMessage="خرابی یافت نشد"
          emptySubtitle="با تغییر فیلتر یا جستجو دوباره تلاش کنید"
          emptyIcon={ReportProblem}
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
          {!loading && visibleFaults.length === 0 && (
            <EmptyState
              title="خرابی یافت نشد"
              subtitle="با تغییر فیلتر یا جستجو دوباره تلاش کنید"
              icon={ReportProblem}
            />
          )}
          {!loading &&
            visibleFaults.map((fault) => (
              <Card
                key={fault.id}
                onClick={() => void openDetail(fault)}
                sx={{ cursor: 'pointer' }}
              >
                <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                  <Stack
                    direction="row"
                    justifyContent="space-between"
                    gap={1.5}
                    alignItems="flex-start"
                  >
                    <Box minWidth={0}>
                      <Typography fontWeight={900} noWrap>
                        {vehiclePlate(vehicleMap.get(String(fault.vehicle_id)), fault.vehicle_id)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {fault.description}
                      </Typography>
                    </Box>
                    <PlainStatusBadge
                      label={faultStatusLabel(fault.status)}
                      tone={statusTone(fault.status)}
                    />
                  </Stack>
                  <Divider sx={{ my: 1.25 }} />
                  <Typography variant="body2" color="text.secondary">
                    شدت: {severityLabel(fault.severity)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    زمان: {formatDateTime(fault.reported_at || fault.created_at)}
                  </Typography>
                </CardContent>
              </Card>
            ))}
        </Stack>
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={closeDetail}
        title={detail?.fault.description || selected?.description || 'جزئیات خرابی'}
        icon={DirectionsCar}
        tabs={tabs}
        loading={detailLoading}
        error={detailError}
        onRetry={selected ? () => void openDetail(selected) : undefined}
        maxWidth="lg"
      />
    </Stack>
  );
}

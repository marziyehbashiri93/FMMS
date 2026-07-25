import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Divider,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  Build,
  CheckCircleOutline,
  DirectionsCar,
  DoNotDisturbAlt,
  FactCheck,
  LocalShipping,
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
import type { Fault, Inspection, RepairOrder, Vehicle } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

const PAGE_SIZE = 50;

const REPAIR_STATUS_LABELS: Record<string, string> = {
  CREATED: 'در انتظار تصمیم ترابری',
  APPROVED: 'ارجاع به تعمیرگاه',
  WORKSHOP_ASSIGNED: 'ارجاع‌شده به تعمیرگاه مرکزی',
  WAITING_EXTERNAL_REFERRAL_APPROVAL: 'منتظر مجوز تعمیرگاه بیرونی',
  REJECTED_BY_TRANSPORT: 'رد شده توسط ترابری',
  CANCELLED: 'لغو شده',
  IN_PROGRESS: 'در حال تعمیر',
  COMPLETED: 'تکمیل شده',
};

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

const WORKSHOP_LABELS: Record<string, string> = {
  INTERNAL: 'تعمیرگاه مرکزی',
  EXTERNAL: 'تعمیرگاه بیرونی',
};

type StatusFilter = '' | 'CREATED' | 'APPROVED';

type DetailState = {
  order: RepairOrder;
  fault: Fault | null;
  vehicle: Vehicle | null;
  checklists: Inspection[];
  faults: Fault[];
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function repairStatusLabel(status: string): string {
  return REPAIR_STATUS_LABELS[status] ?? status;
}

function faultStatusLabel(status: string): string {
  return FAULT_STATUS_LABELS[status] ?? status;
}

function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity] ?? severity;
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'CREATED') return 'warning';
  if (status === 'APPROVED' || status === 'WORKSHOP_ASSIGNED') return 'success';
  if (status === 'REJECTED_BY_TRANSPORT' || status === 'CANCELLED') return 'error';
  return 'neutral';
}

function vehiclePlate(vehicle: Vehicle | undefined | null, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

/**
 * Transport supervisor inbox for repair-needed decisions and workshop selection.
 */
export function TransportRepairsPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [orders, setOrders] = useState<RepairOrder[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [faultSummaries, setFaultSummaries] = useState<Map<string, Fault>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [status, setStatus] = useState<StatusFilter>('CREATED');
  const [selected, setSelected] = useState<RepairOrder | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [actionError, setActionError] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [workshopType, setWorkshopType] = useState<'INTERNAL' | 'EXTERNAL'>('INTERNAL');
  const [workshopId, setWorkshopId] = useState('');
  const [actionLoading, setActionLoading] = useState<'approve' | 'reject' | 'workshop' | ''>('');
  const [success, setSuccess] = useState('');

  const vehicleMap = useMemo(() => {
    const map = new Map<string, Vehicle>();
    vehicles.forEach((vehicle) => map.set(String(vehicle.id), vehicle));
    return map;
  }, [vehicles]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const orderPage = await api.listRepairOrders({
        status: status || undefined,
        page: 1,
        pageSize: PAGE_SIZE,
      });
      const nextOrders = orderPage.results ?? [];
      setOrders(nextOrders);

      const vehicleIds = [...new Set(nextOrders.map((order) => order.vehicle_id).filter(Boolean))];
      const faultIds = [
        ...new Set(nextOrders.map((order) => order.fault_id).filter(Boolean)),
      ];

      const [vehicleResults, faultResults] = await Promise.all([
        Promise.all(
          vehicleIds.map(async (id) => {
            try {
              return await api.getVehicle(id);
            } catch {
              return null;
            }
          }),
        ),
        Promise.all(
          faultIds.map(async (id) => {
            try {
              return await api.getFault(id);
            } catch {
              return null;
            }
          }),
        ),
      ]);

      setVehicles(vehicleResults.filter((item): item is Vehicle => Boolean(item)));
      const nextFaults = new Map<string, Fault>();
      faultResults.forEach((fault) => {
        if (fault) nextFaults.set(fault.id, fault);
      });
      setFaultSummaries(nextFaults);
    } catch (err) {
      setOrders([]);
      setVehicles([]);
      setFaultSummaries(new Map());
      setError(err instanceof Error ? err.message : 'دریافت صف ترابری انجام نشد');
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  const kpi = useMemo(() => {
    const created = orders.filter((item) => item.status === 'CREATED').length;
    const approved = orders.filter((item) => item.status === 'APPROVED').length;
    return { total: orders.length, created, approved };
  }, [orders]);

  const openDetail = async (order: RepairOrder) => {
    setSelected(order);
    setRejectReason('');
    setWorkshopType('INTERNAL');
    setWorkshopId('');
    setDetail(null);
    setDetailError('');
    setActionError('');
    setDetailLoading(true);
    try {
      const [freshOrder, fault, vehicle, checklists, vehicleFaults] = await Promise.all([
        api.getRepairOrder(order.id),
        order.fault_id
          ? api.getFault(order.fault_id).catch(() => null)
          : Promise.resolve(null),
        api.getVehicle(order.vehicle_id),
        api.listVehicleChecklists(order.vehicle_id, { page: 1, pageSize: 20 }),
        api.listFaults(order.vehicle_id, { page: 1, pageSize: 20 }),
      ]);
      setSelected(freshOrder);
      setDetail({
        order: freshOrder,
        fault,
        vehicle,
        checklists: normalizePaginated(checklists),
        faults: vehicleFaults.results ?? [],
      });
      setVehicles((current) => {
        if (current.some((item) => item.id === vehicle.id)) return current;
        return [...current, vehicle];
      });
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات درخواست انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeDetail = () => {
    setSelected(null);
    setDetail(null);
    setDetailError('');
    setActionError('');
    setRejectReason('');
    setWorkshopType('INTERNAL');
    setWorkshopId('');
    setActionLoading('');
  };

  const refreshOrderInDetail = async (orderId: string, preferredStatus?: StatusFilter) => {
    if (preferredStatus) setStatus(preferredStatus);
    const refreshed = await api.listRepairOrders({
      status: preferredStatus || status || undefined,
      page: 1,
      pageSize: PAGE_SIZE,
    });
    const nextOrders = refreshed.results ?? [];
    setOrders(nextOrders);
    const next = nextOrders.find((item) => item.id === orderId) ?? null;
    if (!next) {
      closeDetail();
      return null;
    }
    setSelected(next);
    setDetail((current) => (current ? { ...current, order: next } : current));
    return next;
  };

  const approveOrder = async () => {
    const order = detail?.order ?? selected;
    if (!order) return;
    setActionLoading('approve');
    setActionError('');
    setSuccess('');
    try {
      await api.approveRepairOrder(order.id);
      setSuccess('تعمیر تایید شد. نوع تعمیرگاه را انتخاب کنید.');
      setRejectReason('');
      await refreshOrderInDetail(order.id, 'APPROVED');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'تایید تعمیر انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const rejectOrder = async () => {
    const order = detail?.order ?? selected;
    if (!order || !rejectReason.trim()) return;
    setActionLoading('reject');
    setActionError('');
    setSuccess('');
    try {
      await api.rejectRepairOrderByTransport(order.id, rejectReason.trim());
      closeDetail();
      setSuccess('درخواست تعمیر رد شد و به صف توزیع برگشت.');
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'رد درخواست انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const assignWorkshop = async () => {
    const order = detail?.order ?? selected;
    if (!order) return;
    if (workshopType === 'EXTERNAL' && !workshopId.trim()) {
      setActionError('برای تعمیرگاه بیرونی، شناسه تعمیرگاه الزامی است.');
      return;
    }
    setActionLoading('workshop');
    setActionError('');
    setSuccess('');
    try {
      await api.assignRepairWorkshop(order.id, {
        workshop_type: workshopType,
        workshop_id: workshopType === 'EXTERNAL' ? workshopId.trim() : undefined,
        reason:
          workshopType === 'EXTERNAL' ? 'درخواست ارجاع به تعمیرگاه بیرونی' : '',
      });
      closeDetail();
      setSuccess(
        workshopType === 'EXTERNAL'
          ? 'درخواست مجوز تعمیرگاه بیرونی ثبت شد.'
          : 'سفارش به تعمیرگاه مرکزی ارجاع شد.',
      );
      await load();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت انتخاب تعمیرگاه انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const resetFilters = () => setStatus('CREATED');
  const hasActiveFilters = status !== 'CREATED';
  const currentOrder = detail?.order ?? selected;
  const canDecide = currentOrder?.status === 'CREATED';
  const workshopAlreadyAssigned = Boolean(currentOrder?.workshop_type);
  const canAssignWorkshop =
    currentOrder?.status === 'APPROVED' && !workshopAlreadyAssigned;

  const columns: Array<RtlDataTableColumn<RepairOrder, string>> = [
    {
      key: 'plate',
      label: 'پلاک خودرو',
      minWidth: 140,
      render: (order) => (
        <Typography fontWeight={800}>
          {vehiclePlate(vehicleMap.get(String(order.vehicle_id)), order.vehicle_id)}
        </Typography>
      ),
    },
    {
      key: 'fault',
      label: 'شرح خرابی',
      minWidth: 220,
      render: (order) => {
        const fault = faultSummaries.get(order.fault_id);
        return (
          <Stack spacing={0.35}>
            <Typography fontWeight={800} noWrap>
              {fault?.description || '—'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {fault?.code || order.fault_id.slice(0, 8)} ·{' '}
              {formatDateTime(order.updated_at)}
            </Typography>
          </Stack>
        );
      },
    },
    {
      key: 'status',
      label: 'وضعیت',
      render: (order) => (
        <PlainStatusBadge
          label={repairStatusLabel(order.status)}
          tone={statusTone(order.status)}
        />
      ),
    },
    {
      key: 'actions',
      label: 'عملیات',
      align: 'center',
      render: (order) => (
        <Button
          size="small"
          variant="outlined"
          onClick={() => void openDetail(order)}
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
                    value={vehiclePlate(detail.vehicle, detail.order.vehicle_id)}
                  />
                  <DetailLine
                    label="شرح"
                    value={detail.fault?.description || '—'}
                  />
                  <DetailLine label="کد خرابی" value={detail.fault?.code || '—'} />
                  <DetailLine
                    label="شدت"
                    value={
                      detail.fault ? severityLabel(detail.fault.severity) : '—'
                    }
                  />
                  <DetailLine
                    label="وضعیت خرابی"
                    value={
                      detail.fault
                        ? faultStatusLabel(detail.fault.status)
                        : '—'
                    }
                  />
                  <DetailLine
                    label="وضعیت سفارش تعمیر"
                    value={repairStatusLabel(detail.order.status)}
                  />
                  <DetailLine
                    label="نوع تعمیرگاه"
                    value={
                      detail.order.workshop_type
                        ? WORKSHOP_LABELS[detail.order.workshop_type] ??
                          detail.order.workshop_type
                        : 'هنوز انتخاب نشده'
                    }
                  />
                  <DetailLine
                    label="PM Notification"
                    value={detail.fault?.sap_notification_number || 'در صف ارسال'}
                  />
                  <DetailLine
                    label="زمان ثبت خرابی"
                    value={
                      detail.fault
                        ? formatDateTime(
                            detail.fault.reported_at || detail.fault.created_at,
                          )
                        : '—'
                    }
                  />
                  <DetailLine
                    label="آخرین به‌روزرسانی سفارش"
                    value={formatDateTime(detail.order.updated_at)}
                  />
                </CardContent>
              </Card>

              {!canDecide && !canAssignWorkshop && !workshopAlreadyAssigned && (
                <Alert severity="info">
                  این سفارش از صف تصمیم ترابری خارج شده است.
                </Alert>
              )}
              {workshopAlreadyAssigned && (
                <Alert
                  severity="info"
                  icon={false}
                  sx={{
                    py: 2,
                    border: '1px solid',
                    borderColor: 'info.main',
                    bgcolor: (theme) =>
                      theme.palette.mode === 'dark'
                        ? 'rgba(2, 136, 209, 0.16)'
                        : 'rgba(2, 136, 209, 0.08)',
                    '& .MuiAlert-message': { width: '100%' },
                  }}
                >
                  <Typography
                    fontWeight={900}
                    fontSize={{ xs: '1rem', sm: '1.1rem' }}
                    color="info.dark"
                    textAlign="center"
                  >
                    تعمیرگاه قبلاً تخصیص داده شده است.
                  </Typography>
                  <Typography
                    mt={0.75}
                    textAlign="center"
                    variant="body2"
                    color="text.secondary"
                    fontWeight={700}
                  >
                    نوع تعمیرگاه:{' '}
                    {WORKSHOP_LABELS[currentOrder?.workshop_type || ''] ??
                      currentOrder?.workshop_type}
                  </Typography>
                </Alert>
              )}
              {actionError && <Alert severity="error">{actionError}</Alert>}

              {canDecide && (
                <Stack spacing={1.5}>
                  <Typography fontWeight={700}>آیا تعمیر انجام شود؟</Typography>
                  <RtlTextField
                    fullWidth
                    label="دلیل رد (در صورت رد)"
                    value={rejectReason}
                    onChange={(event) => setRejectReason(event.target.value)}
                    multiline
                    minRows={2}
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
                      loading={actionLoading === 'approve'}
                      disabled={actionLoading !== ''}
                      onClick={() => void approveOrder()}
                      sx={{
                        height: 40,
                        minHeight: 40,
                        px: 1.75,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                      }}
                    >
                      بله — تایید تعمیر
                    </Button>
                    <Button
                      color="error"
                      variant="contained"
                      size="small"
                      startIcon={<DoNotDisturbAlt />}
                      loading={actionLoading === 'reject'}
                      disabled={actionLoading !== '' || !rejectReason.trim()}
                      onClick={() => void rejectOrder()}
                      sx={{
                        height: 40,
                        minHeight: 40,
                        px: 1.75,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                      }}
                    >
                      خیر — رد تعمیر
                    </Button>
                  </Stack>
                </Stack>
              )}

              {canAssignWorkshop && (
                <Stack spacing={1.5}>
                  <Typography fontWeight={700}>انتخاب نوع تعمیرگاه</Typography>
                  <RtlSelectField
                    label="نوع تعمیرگاه"
                    value={workshopType}
                    size="small"
                    onChange={(event) =>
                      setWorkshopType(event.target.value as 'INTERNAL' | 'EXTERNAL')
                    }
                  >
                    <MenuItem value="INTERNAL">تعمیرگاه مرکزی</MenuItem>
                    <MenuItem value="EXTERNAL">تعمیرگاه بیرونی</MenuItem>
                  </RtlSelectField>
                  {workshopType === 'EXTERNAL' && (
                    <RtlTextField
                      fullWidth
                      label="شناسه تعمیرگاه بیرونی"
                      placeholder="مثلاً EXT-001"
                      value={workshopId}
                      onChange={(event) => setWorkshopId(event.target.value)}
                    />
                  )}
                  <Stack direction="row" justifyContent="flex-end">
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<Build />}
                      loading={actionLoading === 'workshop'}
                      disabled={
                        actionLoading !== '' ||
                        (workshopType === 'EXTERNAL' && !workshopId.trim())
                      }
                      onClick={() => void assignWorkshop()}
                      sx={{
                        height: 40,
                        minHeight: 40,
                        px: 1.75,
                        whiteSpace: 'nowrap',
                        flexShrink: 0,
                      }}
                    >
                      ثبت انتخاب تعمیرگاه
                    </Button>
                  </Stack>
                </Stack>
              )}
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
                  value={
                    detail.vehicle.driver1?.name ||
                    detail.vehicle.driver1?.customer_number ||
                    '—'
                  }
                />
                <DetailLine
                  label="کمک راننده"
                  value={
                    detail.vehicle.driver2?.name ||
                    detail.vehicle.driver2?.customer_number ||
                    '—'
                  }
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
                      {toFaNumber(
                        inspection.items.filter((item) => item.result === 'FAIL').length,
                      )}
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
            const historyFaults = detail.faults.filter(
              (fault) => fault.id !== detail.fault?.id,
            );
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
        title="کارتابل ترابری"
        breadcrumbs={[{ label: 'ترابری' }, { label: 'درخواست‌های تعمیر' }]}
      />

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(2, minmax(0, 1fr))',
            md: 'repeat(3, minmax(0, 1fr))',
          },
          gap: 1.5,
        }}
      >
        <KpiCard
          label="موارد صف"
          value={loading ? '...' : toFaNumber(kpi.total)}
          icon={LocalShipping}
        />
        <KpiCard
          label="منتظر تصمیم"
          value={loading ? '...' : toFaNumber(kpi.created)}
          icon={Build}
          tone="warning"
        />
        <KpiCard
          label="ارجاع به تعمیرگاه"
          value={loading ? '...' : toFaNumber(kpi.approved)}
          icon={CheckCircleOutline}
          tone="success"
        />
      </Box>

      <FilterPanel>
        <RtlSelectField<StatusFilter>
          value={status}
          label="وضعیت صف"
          size="small"
          fullWidth={false}
          displayEmpty
          onChange={(event) => setStatus(event.target.value as StatusFilter)}
          sx={{ width: { xs: '100%', md: 260 }, flexShrink: 0 }}
        >
          <MenuItem value="">همه</MenuItem>
          <MenuItem value="CREATED">در انتظار تصمیم</MenuItem>
          <MenuItem value="APPROVED">ارجاع به تعمیرگاه</MenuItem>
        </RtlSelectField>
        <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
      </FilterPanel>

      {success && <Alert severity="success">{success}</Alert>}
      {error && <ErrorState message={error} onRetry={() => void load()} />}

      {!error && !isMobile && (
        <RtlDataTable
          columns={columns}
          rows={orders}
          getRowKey={(order) => order.id}
          loading={loading}
          emptyMessage="درخواستی در صف ترابری نیست"
          emptyIcon={LocalShipping}
          minWidth={900}
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
          {!loading && orders.length === 0 && (
            <EmptyState title="درخواستی در صف ترابری نیست" icon={LocalShipping} />
          )}
          {!loading &&
            orders.map((order) => (
              <Card
                key={order.id}
                onClick={() => void openDetail(order)}
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
                        {vehiclePlate(
                          vehicleMap.get(String(order.vehicle_id)),
                          order.vehicle_id,
                        )}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" noWrap>
                        {faultSummaries.get(order.fault_id)?.description || 'سفارش تعمیر'}
                      </Typography>
                    </Box>
                    <PlainStatusBadge
                      label={repairStatusLabel(order.status)}
                      tone={statusTone(order.status)}
                    />
                  </Stack>
                  <Divider sx={{ my: 1.25 }} />
                  <Typography variant="body2" color="text.secondary">
                    زمان: {formatDateTime(order.updated_at)}
                  </Typography>
                </CardContent>
              </Card>
            ))}
        </Stack>
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={closeDetail}
        title={
          selected
            ? vehiclePlate(
                detail?.vehicle ?? vehicleMap.get(String(selected.vehicle_id)),
                selected.vehicle_id,
              )
            : 'جزئیات درخواست تعمیر'
        }
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

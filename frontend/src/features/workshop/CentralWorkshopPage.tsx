import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  Build,
  CheckCircleOutline,
  DoNotDisturbAlt,
  Inventory2,
} from '@mui/icons-material';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import {
  EMPTY_MATERIAL_PICK,
  MaterialStockPicker,
  type MaterialPickValue,
} from '../../components/MaterialStockPicker';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState } from '../../components/States';
import { PlainStatusBadge, VehicleStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import { StatusFilterTabs, type StatusTabOption } from '../../components/StatusFilterTabs';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type { Fault, RepairOrder, Vehicle } from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

type PartLineDraft = {
  key: string;
  materialNumber: string;
  quantity: number;
  fromCatalog: boolean;
  materialName: string;
  availableQuantity: string;
};

function draftFromPick(part: MaterialPickValue, quantity: number): PartLineDraft {
  return {
    key: `${part.materialNumber}-${Date.now()}`,
    materialNumber: part.materialNumber.trim(),
    quantity,
    fromCatalog: part.fromCatalog,
    materialName: part.materialName,
    availableQuantity: part.availableQuantity || '0',
  };
}

function lineChipLabel(line: PartLineDraft): string {
  const name = line.materialName ? ` · ${line.materialName}` : '';
  const stock = line.fromCatalog
    ? ` · موجودی ${toFaNumber(line.availableQuantity || '0')}`
    : ' · خارج از انبار';
  return `${line.materialNumber}${name}${stock} · تعداد ${toFaNumber(line.quantity)}`;
}

const REPAIR_STATUS_LABELS: Record<string, string> = {
  WORKSHOP_ASSIGNED: 'صف تعمیرگاه مرکزی',
  WAITING_WORKSHOP_CONFIRMATION: 'در انتظار تصمیم فنی',
  IN_PROGRESS: 'در حال تعمیر',
  WAITING_PARTS: 'در انتظار قطعات',
  NO_REPAIR_NEEDED: 'عدم نیاز به تعمیر',
  WAITING_DRIVER_CONFIRMATION: 'منتظر تایید راننده',
  COMPLETED: 'تکمیل شده',
};

type StatusFilter =
  | ''
  | 'WORKSHOP_ASSIGNED'
  | 'IN_PROGRESS'
  | 'WAITING_PARTS'
  | 'NO_REPAIR_NEEDED';

const STATUS_TAB_OPTIONS: ReadonlyArray<StatusTabOption<Exclude<StatusFilter, ''>>> = [
  { value: '', label: 'همه' },
  { value: 'WORKSHOP_ASSIGNED', label: 'صف تصمیم فنی' },
  { value: 'IN_PROGRESS', label: 'در حال تعمیر' },
  { value: 'WAITING_PARTS', label: 'در انتظار قطعات' },
  { value: 'NO_REPAIR_NEEDED', label: 'عدم نیاز به تعمیر' },
];

type DetailState = {
  order: RepairOrder;
  fault: Fault | null;
  vehicle: Vehicle | null;
  history: RepairOrder[];
  timeline: Array<{ event_type: string; description: string; created_at: string }>;
  materialRequests: Array<Record<string, unknown>>;
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function statusLabel(status: string): string {
  return REPAIR_STATUS_LABELS[status] ?? status;
}

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'IN_PROGRESS' || status === 'COMPLETED') return 'success';
  if (status === 'WAITING_PARTS' || status === 'WORKSHOP_ASSIGNED') return 'warning';
  if (status === 'NO_REPAIR_NEEDED') return 'neutral';
  return 'neutral';
}

function vehiclePlate(vehicle: Vehicle | null | undefined, vehicleId: string): string {
  if (!vehicle) return vehicleId.slice(0, 8);
  return vehicle.license_plate || vehicle.vehicle_number || vehicleId.slice(0, 8);
}

/**
 * Central workshop inbox for technical inspection and parts handling.
 */
export function CentralWorkshopPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [items, setItems] = useState<RepairOrder[]>([]);
  const [vehicles, setVehicles] = useState<Map<string, Vehicle>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusTab, setStatusTab] = useState<StatusFilter>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const status = statusTab || statusFilter;
  const [kpiCounts, setKpiCounts] = useState({
    queue: 0,
    inProgress: 0,
    waitingParts: 0,
  });
  const [selected, setSelected] = useState<RepairOrder | null>(null);
  const [detail, setDetail] = useState<DetailState | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [decisionNote, setDecisionNote] = useState('');
  const [requestPart, setRequestPart] = useState<MaterialPickValue>(EMPTY_MATERIAL_PICK);
  const [requestQty, setRequestQty] = useState('1');
  const [requestLines, setRequestLines] = useState<PartLineDraft[]>([]);
  const [consumedPart, setConsumedPart] = useState<MaterialPickValue>(EMPTY_MATERIAL_PICK);
  const [consumedQty, setConsumedQty] = useState('1');
  const [consumedLines, setConsumedLines] = useState<PartLineDraft[]>([]);
  const [actionLoading, setActionLoading] = useState('');
  const [actionError, setActionError] = useState('');
  const [success, setSuccess] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const statuses: string[] = status
        ? [status]
        : ['WORKSHOP_ASSIGNED', 'IN_PROGRESS', 'WAITING_PARTS', 'NO_REPAIR_NEEDED'];
      const pages = await Promise.all(
        statuses.map((itemStatus) =>
          api.listRepairOrders({
            status: itemStatus,
            workshopType: 'INTERNAL',
            page: 1,
            pageSize: 100,
          }),
        ),
      );
      const list = pages.flatMap((page) => normalizePaginated(page));
      list.sort((a, b) => String(b.updated_at ?? '').localeCompare(String(a.updated_at ?? '')));
      setItems(list);

      const vehicleIds = [...new Set(list.map((item) => item.vehicle_id))];
      const vehicleResults = await Promise.all(
        vehicleIds.map(async (id) => {
          try {
            return await api.getVehicle(id);
          } catch {
            return null;
          }
        }),
      );
      const nextVehicles = new Map<string, Vehicle>();
      vehicleResults.forEach((vehicle) => {
        if (vehicle) nextVehicles.set(vehicle.id, vehicle);
      });
      setVehicles(nextVehicles);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : 'دریافت کارتابل تعمیرگاه انجام نشد');
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  const refreshKpis = useCallback(async () => {
    try {
      const statuses = [
        'WORKSHOP_ASSIGNED',
        'IN_PROGRESS',
        'WAITING_PARTS',
        'NO_REPAIR_NEEDED',
      ] as const;
      const pages = await Promise.all(
        statuses.map((itemStatus) =>
          api.listRepairOrders({
            status: itemStatus,
            workshopType: 'INTERNAL',
            page: 1,
            pageSize: 100,
          }),
        ),
      );
      const list = pages.flatMap((page) => normalizePaginated(page));
      setKpiCounts({
        queue: list.filter((item) => item.status === 'WORKSHOP_ASSIGNED').length,
        inProgress: list.filter((item) => item.status === 'IN_PROGRESS').length,
        waitingParts: list.filter((item) => item.status === 'WAITING_PARTS').length,
      });
    } catch {
      // Keep last KPI snapshot; list error is handled separately.
    }
  }, []);

  useEffect(() => {
    void refreshKpis();
  }, [refreshKpis]);

  const openDetail = async (row: RepairOrder) => {
    setSelected(row);
    setDetail(null);
    setDetailError('');
    setActionError('');
    setSuccess('');
    setDecisionNote('');
    setDetailLoading(true);
    try {
      const [order, fault, vehicle, history, timeline, materials] = await Promise.all([
        api.getRepairOrder(row.id),
        api.getFault(row.fault_id).catch(() => null),
        api.getVehicle(row.vehicle_id).catch(() => null),
        api
          .listRepairOrders({ vehicleId: row.vehicle_id, page: 1, pageSize: 20 })
          .then(normalizePaginated)
          .catch(() => [] as RepairOrder[]),
        api.getRepairOrderTimeline(row.id).catch(() => []),
        api.listMaterialRequests().catch(() => []),
      ]);
      setDetail({
        order,
        fault,
        vehicle,
        history: history.filter((item) => item.id !== order.id),
        timeline,
        materialRequests: materials.filter(
          (item) => String(item.repair_order_id) === order.id,
        ),
      });
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const decide = async (repairable: boolean) => {
    if (!selected) return;
    setActionLoading(repairable ? 'repairable' : 'no-repair');
    setActionError('');
    try {
      const result = await api.workshopTechnicalDecision(selected.id, {
        repairable,
        note: decisionNote,
      });
      setSuccess(result.message);
      await Promise.all([load(), refreshKpis()]);
      await openDetail({ ...selected, status: result.status });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت تصمیم انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const addRequestLine = () => {
    if (!requestPart.materialNumber.trim()) return;
    const quantity = Math.max(1, Number(requestQty) || 1);
    setRequestLines((prev) => [...prev, draftFromPick(requestPart, quantity)]);
    setRequestPart(EMPTY_MATERIAL_PICK);
    setRequestQty('1');
  };

  const requestParts = async () => {
    if (!selected) return;
    if (requestLines.length === 0) return;
    setActionLoading('parts');
    setActionError('');
    try {
      await api.createRepairMaterialRequest(
        selected.id,
        requestLines.map((line) => ({
          material_number: line.materialNumber,
          quantity: line.quantity,
          from_catalog: line.fromCatalog,
        })),
      );
      setSuccess('درخواست قطعه ثبت شد و سفارش در انتظار قطعات قرار گرفت.');
      setRequestPart(EMPTY_MATERIAL_PICK);
      setRequestQty('1');
      setRequestLines([]);
      await Promise.all([load(), refreshKpis()]);
      await openDetail(selected);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت درخواست قطعه انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const receiveParts = async (materialRequestId: string) => {
    if (!selected) return;
    setActionLoading(`receive-${materialRequestId}`);
    setActionError('');
    try {
      await api.receiveMaterialRequest(materialRequestId);
      setSuccess('دریافت قطعات ثبت شد؛ تعمیر ادامه می‌یابد.');
      await Promise.all([load(), refreshKpis()]);
      await openDetail(selected);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت دریافت قطعات انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const addConsumedLine = () => {
    if (!consumedPart.materialNumber.trim()) return;
    const quantity = Math.max(1, Number(consumedQty) || 1);
    setConsumedLines((prev) => [...prev, draftFromPick(consumedPart, quantity)]);
    setConsumedPart(EMPTY_MATERIAL_PICK);
    setConsumedQty('1');
  };

  const recordConsumedPart = async () => {
    if (!selected) return;
    if (consumedLines.length === 0) return;
    setActionLoading('consumed');
    setActionError('');
    try {
      for (const line of consumedLines) {
        await api.addRepairPart(selected.id, {
          material_number: line.materialNumber,
          quantity: line.quantity,
        });
      }
      setSuccess('قطعه مصرفی ثبت شد (جدا از درخواست قطعه).');
      setConsumedPart(EMPTY_MATERIAL_PICK);
      setConsumedQty('1');
      setConsumedLines([]);
      await openDetail(selected);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت قطعه مصرفی انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const completeRepair = async (noPartsConsumed = false) => {
    if (!selected) return;
    setActionLoading(noPartsConsumed ? 'complete-empty' : 'complete');
    setActionError('');
    try {
      await api.completeRepairOrder(selected.id, {
        completed_at: new Date().toISOString(),
        no_parts_consumed: noPartsConsumed,
      });
      setSuccess('تعمیر تکمیل شد و برای تایید راننده ارسال شد.');
      setSelected(null);
      await Promise.all([load(), refreshKpis()]);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'تکمیل تعمیر انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const queueCount = kpiCounts.queue;
  const inProgressCount = kpiCounts.inProgress;
  const waitingPartsCount = kpiCounts.waitingParts;

  const columns: Array<RtlDataTableColumn<RepairOrder, string>> = useMemo(
    () => [
      {
        key: 'plate',
        label: 'پلاک',
        render: (row) => (
          <Typography fontWeight={800}>
            {vehiclePlate(vehicles.get(row.vehicle_id), row.vehicle_id)}
          </Typography>
        ),
      },
      {
        key: 'status',
        label: 'وضعیت',
        render: (row) => (
          <PlainStatusBadge label={statusLabel(row.status)} tone={statusTone(row.status)} />
        ),
      },
      {
        key: 'sap',
        label: 'PM Order',
        render: (row) => row.sap_order_number || '—',
      },
      {
        key: 'updated',
        label: 'به‌روزرسانی',
        render: (row) => formatDateTime(row.updated_at),
      },
      {
        key: 'actions',
        label: 'عملیات',
        align: 'center',
        render: (row) => (
          <Button
            size="small"
            variant="outlined"
            onClick={() => void openDetail(row)}
            sx={{ height: 36, minHeight: 36, px: 1.5 }}
          >
            بررسی
          </Button>
        ),
      },
    ],
    [vehicles],
  );

  const canDecide =
    detail?.order.status === 'WORKSHOP_ASSIGNED' ||
    detail?.order.status === 'WAITING_WORKSHOP_CONFIRMATION';
  const canRequestParts = detail?.order.status === 'IN_PROGRESS';
  const canReceiveParts = detail?.order.status === 'WAITING_PARTS';
  const canCompleteRepair = detail?.order.status === 'IN_PROGRESS';
  const canRecordConsumed = detail?.order.status === 'IN_PROGRESS';

  const tabs = detail
    ? [
        {
          label: 'تصمیم فنی',
          content: (
            <Stack spacing={2}>
              <Card variant="outlined">
                <CardContent>
                  <DetailLine
                    label="پلاک"
                    value={vehiclePlate(detail.vehicle, detail.order.vehicle_id)}
                  />
                  <DetailLine
                    label="وضعیت خودرو"
                    value={
                      detail.vehicle ? (
                        <VehicleStatusBadge status={detail.vehicle.status} />
                      ) : (
                        '—'
                      )
                    }
                  />
                  <DetailLine label="علت خرابی" value={detail.fault?.description || '—'} />
                  <DetailLine
                    label="شرح راننده"
                    value={detail.fault?.description || '—'}
                  />
                  <DetailLine
                    label="یادداشت توزیع"
                    value={detail.fault?.distribution_decision_note || '—'}
                  />
                  <DetailLine
                    label="یادداشت ترابری"
                    value={detail.order.transport_approval_note || '—'}
                  />
                  <DetailLine
                    label="یادداشت تعمیرگاه"
                    value={detail.order.workshop_decision_note || '—'}
                  />
                  <DetailLine
                    label="PM Order"
                    value={detail.order.sap_order_number || 'هنوز ایجاد نشده'}
                  />
                  <DetailLine
                    label="وضعیت سفارش"
                    value={statusLabel(detail.order.status)}
                  />
                </CardContent>
              </Card>

              {success && <Alert severity="success">{success}</Alert>}
              {actionError && <Alert severity="error">{actionError}</Alert>}

              {canDecide && (
                <>
                  <RtlTextField
                    fullWidth
                    label="یادداشت تصمیم فنی"
                    value={decisionNote}
                    onChange={(event) => setDecisionNote(event.target.value)}
                  />
                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} useFlexGap>
                    <Button
                      color="success"
                      variant="contained"
                      startIcon={<CheckCircleOutline />}
                      loading={actionLoading === 'repairable'}
                      onClick={() => void decide(true)}
                    >
                      نیاز به تعمیر دارد
                    </Button>
                    <Button
                      color="inherit"
                      variant="outlined"
                      startIcon={<DoNotDisturbAlt />}
                      loading={actionLoading === 'no-repair'}
                      onClick={() => void decide(false)}
                    >
                      عدم نیاز به تعمیر
                    </Button>
                  </Stack>
                </>
              )}

              {canRequestParts && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={700} mb={1.5}>
                      درخواست قطعه
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mb={1.5}>
                      برای هر قطعه تعداد جداگانه وارد کنید؛ سپس به لیست اضافه کرده و درخواست را ثبت کنید.
                    </Typography>
                    <Stack spacing={1.5}>
                      <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1}
                        useFlexGap
                        alignItems="flex-start"
                      >
                        <MaterialStockPicker
                          label="قطعه درخواستی"
                          value={requestPart}
                          onChange={setRequestPart}
                          showSelectedChip={false}
                        />
                        <RtlTextField
                          label="تعداد"
                          value={requestQty}
                          onChange={(event) => setRequestQty(event.target.value)}
                          size="small"
                          type="number"
                          inputProps={{ min: 1 }}
                          sx={{ width: { xs: '100%', sm: 110 } }}
                        />
                        <Button
                          variant="outlined"
                          disabled={!requestPart.materialNumber.trim()}
                          onClick={addRequestLine}
                          sx={{ mt: { sm: 0.5 } }}
                        >
                          افزودن به لیست
                        </Button>
                      </Stack>
                      {requestLines.length > 0 ? (
                        <Stack direction="row" flexWrap="wrap" gap={1}>
                          {requestLines.map((line) => (
                            <Chip
                              key={line.key}
                              color={line.fromCatalog ? 'default' : 'warning'}
                              variant="outlined"
                              label={lineChipLabel(line)}
                              onDelete={() =>
                                setRequestLines((prev) =>
                                  prev.filter((item) => item.key !== line.key),
                                )
                              }
                            />
                          ))}
                        </Stack>
                      ) : null}
                      <Stack
                        direction="row"
                        justifyContent="flex-end"
                        sx={{
                          pt: 1,
                          borderTop: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Button
                          variant="contained"
                          startIcon={<Inventory2 />}
                          loading={actionLoading === 'parts'}
                          disabled={requestLines.length === 0}
                          onClick={() => void requestParts()}
                        >
                          ثبت درخواست
                        </Button>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {canReceiveParts && (
                <Stack spacing={1}>
                  {detail.materialRequests.length === 0 ? (
                    <Alert severity="info">درخواست قطعه‌ای برای دریافت ثبت نشده است.</Alert>
                  ) : (
                    detail.materialRequests.map((item) => (
                      <Card key={String(item.id)} variant="outlined">
                        <CardContent
                          sx={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: 1,
                          }}
                        >
                          <Box>
                            <Typography fontWeight={700}>
                              درخواست {String(item.id).slice(0, 8)}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              وضعیت: {String(item.status)}
                            </Typography>
                          </Box>
                          <Button
                            size="small"
                            variant="contained"
                            loading={actionLoading === `receive-${String(item.id)}`}
                            disabled={item.status !== 'STOCK_ISSUED'}
                            onClick={() => void receiveParts(String(item.id))}
                          >
                            ثبت دریافت فیزیکی
                          </Button>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </Stack>
              )}

              {canRecordConsumed && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography fontWeight={700} mb={1.5}>
                      قطعات مصرفی (واقعی)
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mb={1.5}>
                      برای هر قطعه مصرفی تعداد جداگانه ثبت کنید (متفاوت از درخواست قطعه).
                    </Typography>
                    <Stack spacing={1.5}>
                      <Stack
                        direction={{ xs: 'column', sm: 'row' }}
                        spacing={1}
                        useFlexGap
                        alignItems="flex-start"
                      >
                        <MaterialStockPicker
                          label="قطعه مصرفی"
                          value={consumedPart}
                          onChange={setConsumedPart}
                          showSelectedChip={false}
                        />
                        <RtlTextField
                          label="تعداد"
                          value={consumedQty}
                          onChange={(event) => setConsumedQty(event.target.value)}
                          size="small"
                          type="number"
                          inputProps={{ min: 1 }}
                          sx={{ width: { xs: '100%', sm: 110 } }}
                        />
                        <Button
                          variant="outlined"
                          disabled={!consumedPart.materialNumber.trim()}
                          onClick={addConsumedLine}
                          sx={{ mt: { sm: 0.5 } }}
                        >
                          افزودن به لیست
                        </Button>
                      </Stack>
                      {consumedLines.length > 0 ? (
                        <Stack direction="row" flexWrap="wrap" gap={1}>
                          {consumedLines.map((line) => (
                            <Chip
                              key={line.key}
                              color={line.fromCatalog ? 'success' : 'warning'}
                              variant="outlined"
                              label={lineChipLabel(line)}
                              onDelete={() =>
                                setConsumedLines((prev) =>
                                  prev.filter((item) => item.key !== line.key),
                                )
                              }
                            />
                          ))}
                        </Stack>
                      ) : null}
                      <Stack
                        direction="row"
                        justifyContent="flex-end"
                        sx={{
                          pt: 1,
                          borderTop: '1px solid',
                          borderColor: 'divider',
                        }}
                      >
                        <Button
                          variant="contained"
                          color="success"
                          loading={actionLoading === 'consumed'}
                          disabled={consumedLines.length === 0}
                          onClick={() => void recordConsumedPart()}
                        >
                          ثبت قطعه مصرفی
                        </Button>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              )}

              {canCompleteRepair && (
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} useFlexGap>
                  <Button
                    color="success"
                    variant="contained"
                    loading={actionLoading === 'complete'}
                    onClick={() => void completeRepair(false)}
                  >
                    تکمیل تعمیر
                  </Button>
                  <Button
                    color="inherit"
                    variant="outlined"
                    loading={actionLoading === 'complete-empty'}
                    onClick={() => void completeRepair(true)}
                  >
                    تکمیل بدون مصرف قطعه
                  </Button>
                </Stack>
              )}
            </Stack>
          ),
        },
        {
          label: 'سوابق تعمیرات',
          content:
            detail.history.length === 0 ? (
              <EmptyState title="سابقه تعمیر دیگری نیست" />
            ) : (
              <Stack spacing={1}>
                {detail.history.map((item) => (
                  <Card key={item.id} variant="outlined">
                    <CardContent>
                      <DetailLine label="وضعیت" value={statusLabel(item.status)} />
                      <DetailLine
                        label="PM Order"
                        value={item.sap_order_number || '—'}
                      />
                      <DetailLine label="زمان" value={formatDateTime(item.updated_at)} />
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ),
        },
        {
          label: 'تاریخچه',
          content:
            detail.timeline.length === 0 ? (
              <EmptyState title="رویدادی ثبت نشده" />
            ) : (
              <Stack spacing={1}>
                {detail.timeline.map((event, index) => (
                  <Card key={`${event.event_type}-${index}`} variant="outlined">
                    <CardContent>
                      <Typography fontWeight={700}>{event.description}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {event.event_type} · {formatDateTime(event.created_at)}
                      </Typography>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            ),
        },
      ]
    : [];

  return (
    <FeaturePage>
      <PageHeader
        title="کارتابل تعمیرگاه مرکزی"
        breadcrumbs={[{ label: 'تعمیرات' }, { label: 'تعمیرگاه مرکزی' }]}
      />

      <KpiGrid>
        <KpiCard label="صف تصمیم فنی" value={toFaNumber(queueCount)} icon={Build} tone="warning" />
        <KpiCard label="در حال تعمیر" value={toFaNumber(inProgressCount)} icon={Build} tone="success" />
        <KpiCard
          label="در انتظار قطعات"
          value={toFaNumber(waitingPartsCount)}
          icon={Inventory2}
          tone="error"
        />
      </KpiGrid>

      <StatusFilterTabs
        value={statusTab}
        options={STATUS_TAB_OPTIONS}
        onChange={(next) => {
          setStatusTab(next);
          if (next) setStatusFilter('');
        }}
        ariaLabel="وضعیت تعمیرگاه مرکزی"
      />

      {statusTab === '' && (
        <FilterPanel>
          <RtlSelectField
            label="وضعیت"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            size="small"
          >
            <MenuItem value="">همه</MenuItem>
            <MenuItem value="WORKSHOP_ASSIGNED">صف تصمیم فنی</MenuItem>
            <MenuItem value="IN_PROGRESS">در حال تعمیر</MenuItem>
            <MenuItem value="WAITING_PARTS">در انتظار قطعات</MenuItem>
            <MenuItem value="NO_REPAIR_NEEDED">عدم نیاز به تعمیر</MenuItem>
          </RtlSelectField>
          <ClearFiltersButton
            onClick={() => setStatusFilter('')}
            disabled={statusFilter === ''}
          />
        </FilterPanel>
      )}

      {error && <ErrorState message={error} onRetry={() => void load()} />}
      {!loading && !error && (
        <RtlDataTable
          rows={items}
          columns={columns}
          getRowKey={(row) => row.id}
          emptyMessage="موردی در کارتابل تعمیرگاه نیست"
          emptySubtitle="پس از ارجاع ترابری به تعمیرگاه مرکزی، اینجا نمایش داده می‌شود."
          loading={loading}
        />
      )}
      {loading && !error && (
        <RtlDataTable rows={[]} columns={columns} loading emptyMessage="در حال بارگذاری" />
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={() => {
          setSelected(null);
          setDetail(null);
        }}
        title="جزئیات درخواست تعمیرگاه مرکزی"
        icon={Build}
        tabs={tabs}
        loading={detailLoading}
        error={detailError}
        onRetry={selected ? () => void openDetail(selected) : undefined}
        maxWidth="lg"
      />

      {isMobile && null}
    </FeaturePage>
  );
}

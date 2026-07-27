import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  MenuItem,
  Stack,
  Typography,
} from '@mui/material';
import { Sync } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { canRunSapFullSync } from '../../app/access';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { DetailLine } from '../../components/DetailLine';
import { FeaturePage, KpiGrid } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { KpiCard } from '../../components/KpiCard';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlSelectField } from '../../components/RtlSelectField';
import { AppTabs } from '../../components/AppTabs';
import { StatusFilterTabs, type StatusTabOption } from '../../components/StatusFilterTabs';
import { TabbedDetailModal } from '../../components/TabbedDetailModal';
import type {
  AuthUser,
  SAPObjectType,
  SAPSyncRun,
  SAPTransaction,
  SAPTransactionStatus,
  SAPTransactionSummary,
} from '../../types/fmms';
import { formatDateTime, toFaNumber } from '../../utils/format';

const STATUS_LABELS: Record<string, string> = {
  PENDING: 'در صف',
  IN_PROGRESS: 'در حال ارسال',
  SUCCESS: 'موفق',
  FAILED: 'ناموفق',
  RETRYING: 'تلاش مجدد',
  EXHAUSTED: 'اتمام تلاش',
  PARTIAL_SUCCESS: 'موفقیت نسبی',
};

const OBJECT_TYPE_OPTIONS: Array<{ value: SAPObjectType | ''; label: string }> = [
  { value: '', label: 'همه بخش‌ها' },
  { value: 'FAULT', label: 'خرابی / اعلان PM' },
  { value: 'REPAIR_ORDER', label: 'تعمیر / سفارش کار' },
  { value: 'VEHICLE', label: 'خودرو' },
  { value: 'MEASUREMENT_DOCUMENT', label: 'کیلومترشمار' },
  { value: 'VEHICLE_ASSIGNMENT', label: 'تخصیص خودرو' },
  { value: 'PM_WORK_ORDER', label: 'نگهداری پیشگیرانه' },
  { value: 'PURCHASE_REQUISITION', label: 'درخواست خرید' },
  { value: 'PURCHASE_ORDER', label: 'سفارش خرید' },
  { value: 'GOODS_RECEIPT', label: 'رسید کالا' },
  { value: 'GOODS_ISSUE', label: 'صدور کالا' },
];

const SYNC_ITEM_LABELS: Record<string, string> = {
  vehicles: 'خودروها',
  inspection_templates: 'قالب بازرسی',
  fault_catalog: 'کاتالوگ خرابی',
  central_stock: 'موجودی انبار مرکزی',
};

type StatusFilter = '' | SAPTransactionStatus;
type MainTab = 0 | 1;

const STATUS_TAB_OPTIONS: ReadonlyArray<StatusTabOption<SAPTransactionStatus>> = [
  { value: '', label: 'همه' },
  ...Object.entries(STATUS_LABELS)
    .filter(([value]) => value !== 'PARTIAL_SUCCESS')
    .map(([value, label]) => ({
      value: value as SAPTransactionStatus,
      label,
    })),
];

function statusTone(status: string): 'success' | 'warning' | 'error' | 'neutral' {
  if (status === 'SUCCESS') return 'success';
  if (status === 'PENDING' || status === 'IN_PROGRESS' || status === 'RETRYING') {
    return 'warning';
  }
  if (status === 'FAILED' || status === 'EXHAUSTED') return 'error';
  return 'neutral';
}

function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function formatJson(value: unknown): string {
  try {
    return JSON.stringify(value ?? {}, null, 2);
  } catch {
    return String(value);
  }
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <Box
      component="pre"
      sx={{
        m: 0,
        p: 1.5,
        borderRadius: (t) => t.radius('md'),
        bgcolor: 'action.hover',
        border: '1px solid',
        borderColor: 'divider',
        fontSize: 12,
        lineHeight: 1.6,
        overflow: 'auto',
        maxHeight: 360,
        direction: 'ltr',
        textAlign: 'left',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      }}
    >
      {formatJson(value)}
    </Box>
  );
}

/**
 * Audit log of SAP write transactions (BAPI) and OData read-sync runs.
 */
export function SapTransactionsPage() {
  const [mainTab, setMainTab] = useState<MainTab>(0);
  const [items, setItems] = useState<SAPTransaction[]>([]);
  const [syncRuns, setSyncRuns] = useState<SAPSyncRun[]>([]);
  const [summary, setSummary] = useState<SAPTransactionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusTab, setStatusTab] = useState<StatusFilter>('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const status = statusTab || statusFilter;
  const [objectType, setObjectType] = useState<SAPObjectType | ''>('');
  const [selected, setSelected] = useState<SAPTransaction | null>(null);
  const [selectedSync, setSelectedSync] = useState<SAPSyncRun | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [user, setUser] = useState<AuthUser | null>(null);
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncMessage, setSyncMessage] = useState('');
  const [syncError, setSyncError] = useState('');

  const canSync = canRunSapFullSync(user);

  useEffect(() => {
    let cancelled = false;
    void api
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const refreshSummary = useCallback(async () => {
    try {
      const txnSummary = await api.getSapTransactionSummary();
      setSummary(txnSummary);
    } catch {
      // Keep last summary snapshot; list error is handled separately.
    }
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const txns = await api.listSapTransactions({
        status: status || undefined,
        objectType: objectType || undefined,
        page: 1,
        pageSize: 100,
      });
      setItems(txns.results ?? []);

      try {
        const syncHistory = await api.listSapSyncHistory({ page: 1, pageSize: 50 });
        setSyncRuns(syncHistory.results ?? []);
      } catch {
        // OData history requires supervisor+; keep BAPI logs available.
        setSyncRuns([]);
      }
    } catch (err) {
      setItems([]);
      setSyncRuns([]);
      setError(err instanceof Error ? err.message : 'دریافت لاگ SAP انجام نشد');
    } finally {
      setLoading(false);
    }
  }, [status, objectType]);

  useEffect(() => {
    void refreshSummary();
  }, [refreshSummary]);

  useEffect(() => {
    void load();
  }, [load]);

  const runManualSync = async () => {
    if (!canSync || syncLoading) return;
    setSyncLoading(true);
    setSyncError('');
    setSyncMessage('');
    try {
      const result = await api.runSapSync();
      const label = statusLabel(result.status);
      setSyncMessage(`همگام‌سازی دستی انجام شد — وضعیت: ${label}`);
      setMainTab(1);
      await Promise.all([load(), refreshSummary()]);
    } catch (err) {
      setSyncError(err instanceof Error ? err.message : 'همگام‌سازی دستی انجام نشد');
    } finally {
      setSyncLoading(false);
    }
  };

  const openDetail = async (row: SAPTransaction) => {
    setSelected(row);
    setDetailError('');
    setDetailLoading(true);
    try {
      const full = await api.getSapTransaction(row.id);
      setSelected(full);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : 'دریافت جزئیات انجام نشد');
    } finally {
      setDetailLoading(false);
    }
  };

  const resetFilters = () => {
    setStatusFilter('');
    setObjectType('');
  };

  const hasActiveFilters = Boolean(statusFilter || objectType);

  const txnColumns: Array<RtlDataTableColumn<SAPTransaction, string>> = useMemo(
    () => [
      {
        key: 'created_at',
        label: 'زمان',
        minWidth: 140,
        render: (row) => formatDateTime(row.created_at),
      },
      {
        key: 'section',
        label: 'بخش',
        minWidth: 140,
        render: (row) => row.section || row.object_type,
      },
      {
        key: 'protocol',
        label: 'پروتکل',
        render: (row) => row.protocol || 'BAPI',
      },
      {
        key: 'status',
        label: 'وضعیت',
        render: (row) => (
          <PlainStatusBadge label={statusLabel(row.status)} tone={statusTone(row.status)} />
        ),
      },
      {
        key: 'sap_document_number',
        label: 'شماره سند SAP',
        render: (row) => row.sap_document_number || '—',
      },
      {
        key: 'idempotency_key',
        label: 'کلید یکتایی',
        minWidth: 160,
        render: (row) => (
          <Typography variant="body2" noWrap title={row.idempotency_key} sx={{ maxWidth: 180 }}>
            {row.idempotency_key}
          </Typography>
        ),
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
            sx={{ height: 36, minHeight: 36, px: 1.5, minWidth: 72 }}
          >
            جزئیات
          </Button>
        ),
      },
    ],
    [],
  );

  const syncColumns: Array<RtlDataTableColumn<SAPSyncRun, string>> = useMemo(
    () => [
      {
        key: 'started_at',
        label: 'شروع',
        minWidth: 140,
        render: (row) => formatDateTime(row.started_at),
      },
      {
        key: 'trigger_source',
        label: 'منبع',
        render: (row) => row.trigger_source,
      },
      {
        key: 'status',
        label: 'وضعیت',
        render: (row) => (
          <PlainStatusBadge label={statusLabel(row.status)} tone={statusTone(row.status)} />
        ),
      },
      {
        key: 'items',
        label: 'آیتم‌ها',
        minWidth: 180,
        render: (row) =>
          row.items.map((item) => SYNC_ITEM_LABELS[item.name] ?? item.name).join('، ') || '—',
      },
      {
        key: 'finished_at',
        label: 'پایان',
        render: (row) => formatDateTime(row.finished_at),
      },
      {
        key: 'actions',
        label: 'عملیات',
        align: 'center',
        render: (row) => (
          <Button
            size="small"
            variant="outlined"
            onClick={() => setSelectedSync(row)}
            sx={{ height: 36, minHeight: 36, px: 1.5, minWidth: 72 }}
          >
            جزئیات
          </Button>
        ),
      },
    ],
    [],
  );

  const detailTabs = selected
    ? [
        {
          label: 'خلاصه',
          content: (
            <Card variant="outlined">
              <CardContent>
                <DetailLine label="بخش" value={selected.section || selected.object_type} />
                <DetailLine label="پروتکل" value={selected.protocol || 'BAPI'} />
                <DetailLine
                  label="وضعیت"
                  value={
                    <PlainStatusBadge
                      label={statusLabel(selected.status)}
                      tone={statusTone(selected.status)}
                    />
                  }
                />
                <DetailLine label="شناسه آبجکت" value={selected.object_id} />
                <DetailLine label="کلید یکتایی" value={selected.idempotency_key} />
                <DetailLine
                  label="شماره سند SAP"
                  value={selected.sap_document_number || '—'}
                />
                <DetailLine
                  label="تلاش"
                  value={`${toFaNumber(selected.retry_count)} / ${toFaNumber(selected.max_retries)}`}
                />
                <DetailLine label="ایجاد" value={formatDateTime(selected.created_at)} />
                <DetailLine label="تکمیل" value={formatDateTime(selected.completed_at)} />
                {selected.error_message && (
                  <DetailLine label="خطا" value={selected.error_message} />
                )}
              </CardContent>
            </Card>
          ),
        },
        {
          label: 'درخواست ارسال‌شده',
          content: <JsonBlock value={selected.request_payload} />,
        },
        {
          label: 'پاسخ SAP',
          content: selected.response_payload ? (
            <JsonBlock value={selected.response_payload} />
          ) : (
            <EmptyState
              title="پاسخی ثبت نشده است"
              subtitle="هنوز پاسخی از SAP دریافت نشده."
            />
          ),
        },
      ]
    : [];

  const syncDetailTabs = selectedSync
    ? [
        {
          label: 'خلاصه',
          content: (
            <Card variant="outlined">
              <CardContent>
                <DetailLine label="منبع" value={selectedSync.trigger_source} />
                <DetailLine
                  label="وضعیت"
                  value={
                    <PlainStatusBadge
                      label={statusLabel(selectedSync.status)}
                      tone={statusTone(selectedSync.status)}
                    />
                  }
                />
                <DetailLine label="Request ID" value={selectedSync.request_id} />
                <DetailLine label="شروع" value={formatDateTime(selectedSync.started_at)} />
                <DetailLine label="پایان" value={formatDateTime(selectedSync.finished_at)} />
                {selectedSync.error && <DetailLine label="خطا" value={selectedSync.error} />}
                <Box mt={2}>
                  <Typography variant="subtitle2" mb={1}>
                    خلاصه اجرا
                  </Typography>
                  <JsonBlock value={selectedSync.summary} />
                </Box>
              </CardContent>
            </Card>
          ),
        },
        {
          label: 'آیتم‌های OData',
          content: (
            <Stack spacing={1.5}>
              {selectedSync.items.map((item) => (
                <Card key={`${item.name}-${item.started_at}`} variant="outlined">
                  <CardContent>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      alignItems="center"
                      mb={1}
                    >
                      <Typography fontWeight={700}>
                        {SYNC_ITEM_LABELS[item.name] ?? item.name}
                      </Typography>
                      <PlainStatusBadge
                        label={statusLabel(item.status)}
                        tone={statusTone(item.status)}
                      />
                    </Stack>
                    <DetailLine label="شروع" value={formatDateTime(item.started_at)} />
                    <DetailLine label="پایان" value={formatDateTime(item.finished_at)} />
                    {item.error && <DetailLine label="خطا" value={item.error} />}
                    <Box mt={1.5}>
                      <JsonBlock value={item.summary} />
                    </Box>
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
        title="لاگ یکپارچه‌سازی SAP"
        breadcrumbs={[{ label: 'مدیریت' }, { label: 'یکپارچه‌سازی SAP' }]}
        actions={
          canSync ? (
            <Button
              variant="contained"
              color="primary"
              startIcon={<Sync />}
              loading={syncLoading}
              onClick={() => void runManualSync()}
            >
              همگام‌سازی دستی
            </Button>
          ) : undefined
        }
      />

      <Alert severity="info">
        تراکنش‌های نوشتن (BAPI) با درخواست و پاسخ کامل ذخیره می‌شوند. همگام‌سازی خواندن
        (OData) در تب جداگانه به‌صورت خلاصه اجرا نمایش داده می‌شود.
      </Alert>

      {syncMessage && <Alert severity="success">{syncMessage}</Alert>}
      {syncError && <Alert severity="error">{syncError}</Alert>}

      {summary && (
        <KpiGrid mdColumns={5}>
          <KpiCard label="کل تراکنش‌ها" value={toFaNumber(summary.total)} icon={Sync} />
          <KpiCard
            label="موفق"
            value={toFaNumber(summary.success)}
            icon={Sync}
            tone="success"
          />
          <KpiCard
            label="ناموفق / تلاش مجدد"
            value={toFaNumber(summary.failed)}
            icon={Sync}
            tone="error"
          />
          <KpiCard
            label="در صف"
            value={toFaNumber(summary.pending)}
            icon={Sync}
            tone="warning"
          />
          <KpiCard
            label="اتمام تلاش"
            value={toFaNumber(summary.exhausted)}
            icon={Sync}
            tone="error"
          />
        </KpiGrid>
      )}

      <AppTabs
        value={mainTab}
        onChange={(value) => setMainTab(value as MainTab)}
        ariaLabel="بخش‌های SAP"
        items={[
          { value: 0, label: 'تراکنش‌های نوشتن (BAPI)' },
          { value: 1, label: 'همگام‌سازی خواندن (OData)' },
        ]}
      />

      {error && (
        <ErrorState
          message={error}
          onRetry={() => {
            void Promise.all([load(), refreshSummary()]);
          }}
        />
      )}
      {loading && !error && <LoadingState label="در حال بارگذاری لاگ SAP..." />}

      {!loading && !error && mainTab === 0 && (
        <>
          <StatusFilterTabs
            value={statusTab}
            options={STATUS_TAB_OPTIONS}
            onChange={(next) => {
              setStatusTab(next);
              if (next) {
                setStatusFilter('');
                setObjectType('');
              }
            }}
            ariaLabel="وضعیت تراکنش SAP"
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
                {Object.entries(STATUS_LABELS)
                  .filter(([value]) => value !== 'PARTIAL_SUCCESS')
                  .map(([value, label]) => (
                    <MenuItem key={value} value={value}>
                      {label}
                    </MenuItem>
                  ))}
              </RtlSelectField>
              <RtlSelectField
                label="بخش"
                value={objectType}
                onChange={(event) => setObjectType(event.target.value as SAPObjectType | '')}
                size="small"
              >
                {OBJECT_TYPE_OPTIONS.map((option) => (
                  <MenuItem key={option.value || 'all'} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </RtlSelectField>
              <ClearFiltersButton onClick={resetFilters} disabled={!hasActiveFilters} />
            </FilterPanel>
          )}

          <RtlDataTable
            rows={items}
            columns={txnColumns}
            getRowKey={(row) => row.id}
            emptyMessage="تراکنشی ثبت نشده"
            emptySubtitle="پس از ارسال به SAP، درخواست و پاسخ اینجا دیده می‌شود."
          />
        </>
      )}

      {!loading && !error && mainTab === 1 && (
        <RtlDataTable
          rows={syncRuns}
          columns={syncColumns}
          getRowKey={(row) => row.id}
          emptyMessage="همگام‌سازی ثبت نشده"
          emptySubtitle="اجراهای OData خواندن اینجا نمایش داده می‌شوند."
        />
      )}

      <TabbedDetailModal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="جزئیات تراکنش SAP"
        icon={Sync}
        tabs={detailTabs}
        loading={detailLoading}
        error={detailError}
        onRetry={selected ? () => void openDetail(selected) : undefined}
        maxWidth="lg"
      />

      <TabbedDetailModal
        open={Boolean(selectedSync)}
        onClose={() => setSelectedSync(null)}
        title="جزئیات همگام‌سازی OData"
        icon={Sync}
        tabs={syncDetailTabs}
        maxWidth="lg"
      />
    </FeaturePage>
  );
}

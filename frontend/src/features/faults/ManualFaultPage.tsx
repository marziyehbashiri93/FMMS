import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
} from '@mui/material';
import { ReportProblem } from '@mui/icons-material';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { FailureSeverity, FaultCatalog, Vehicle } from '../../types/fmms';

const VEHICLE_PAGE_SIZE = 100;
const CATALOG_PAGE_SIZE = 500;

const SEVERITY_LABELS: Record<FailureSeverity, string> = {
  LOW: 'کم',
  MEDIUM: 'متوسط',
  HIGH: 'زیاد',
  CRITICAL: 'بحرانی',
};

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function severityFromDefectClass(defectClass: string): FailureSeverity {
  const value = defectClass.trim().toUpperCase();
  if (value === 'S1') return 'CRITICAL';
  if (value === 'S2') return 'HIGH';
  if (value === 'S3') return 'MEDIUM';
  return 'LOW';
}

export function ManualFaultPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [catalogs, setCatalogs] = useState<FaultCatalog[]>([]);
  const [vehicleId, setVehicleId] = useState('');
  const [catalogId, setCatalogId] = useState('');
  const [description, setDescription] = useState('');
  const [bootLoading, setBootLoading] = useState(true);
  const [bootError, setBootError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      setBootLoading(true);
      setBootError('');
      try {
        const [vehiclePage, catalogPage] = await Promise.all([
          api.listVehicles('', 'license_plate', { page: 1, pageSize: VEHICLE_PAGE_SIZE }),
          api.listFaultCatalogs({ page: 1, pageSize: CATALOG_PAGE_SIZE }),
        ]);
        if (cancelled) return;
        setVehicles(vehiclePage.results);
        setCatalogs(normalizePaginated(catalogPage).filter((item) => item.is_active));
      } catch (err) {
        if (!cancelled) {
          setBootError(err instanceof Error ? err.message : 'آماده‌سازی فرم ثبت خرابی انجام نشد');
        }
      } finally {
        if (!cancelled) setBootLoading(false);
      }
    };
    void boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedCatalog = useMemo(
    () => catalogs.find((item) => item.id === catalogId) ?? null,
    [catalogId, catalogs],
  );
  const severity = selectedCatalog ? severityFromDefectClass(selectedCatalog.defect_class) : null;

  const submit = async () => {
    if (!vehicleId || !selectedCatalog || !severity) {
      setSubmitError('انتخاب خودرو و خرابی الزامی است.');
      return;
    }
    setSubmitting(true);
    setSubmitError('');
    setSuccess('');
    try {
      await api.reportFault({
        vehicle_id: vehicleId,
        code: selectedCatalog.code,
        description: description.trim() || selectedCatalog.code_text,
        severity,
      });
      setSuccess('خرابی ثبت شد.');
      setCatalogId('');
      setDescription('');
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'ثبت خرابی انجام نشد');
    } finally {
      setSubmitting(false);
    }
  };

  if (bootLoading) return <LoadingState label="در حال آماده‌سازی فرم ثبت خرابی" />;
  if (bootError) return <ErrorState message={bootError} onRetry={() => window.location.reload()} />;

  return (
    <Stack spacing={{ xs: 1.5, md: 2.25 }} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="ثبت خرابی موردی"
        breadcrumbs={[
          { label: 'مدیریت ناوگان', to: '/vehicles' },
          { label: 'ثبت خرابی' },
        ]}
      />

      <Card>
        <CardContent sx={{ p: { xs: 1.75, md: 2.25 }, display: 'grid', gap: 1.75 }}>
          {!catalogs.length && (
            <EmptyState
              title="کاتالوگ خرابی یافت نشد"
              subtitle="ابتدا همگام‌سازی SAP را اجرا کنید."
            />
          )}

          <RtlSelectField
            label="خودرو"
            value={vehicleId}
            displayEmpty
            onChange={(event) => setVehicleId(String(event.target.value))}
          >
            <MenuItem value="">
              <em>انتخاب خودرو</em>
            </MenuItem>
            {vehicles.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.vehicle_number} - {item.license_plate}
              </MenuItem>
            ))}
          </RtlSelectField>

          <RtlSelectField
            label="خرابی"
            value={catalogId}
            displayEmpty
            onChange={(event) => setCatalogId(String(event.target.value))}
          >
            <MenuItem value="">
              <em>انتخاب خرابی</em>
            </MenuItem>
            {catalogs.map((item) => (
              <MenuItem key={item.id} value={item.id}>
                {item.group_text} - {item.code} - {item.code_text}
              </MenuItem>
            ))}
          </RtlSelectField>

          {selectedCatalog && severity && (
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
              <Chip label={selectedCatalog.group_text} size="small" />
              <Chip label={selectedCatalog.defect_class_text} size="small" color="warning" />
              <Chip label={`شدت: ${SEVERITY_LABELS[severity]}`} size="small" color="error" />
            </Stack>
          )}

          <RtlTextField
            label="شرح تکمیلی"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            multiline
            minRows={4}
            placeholder={selectedCatalog?.code_text || ''}
          />

          {submitError && <Alert severity="error">{submitError}</Alert>}
          {success && <Alert severity="success">{success}</Alert>}

          <Stack direction="row" justifyContent="flex-start">
            <Button
              variant="contained"
              startIcon={<ReportProblem />}
              loading={submitting}
              disabled={!catalogs.length}
              onClick={submit}
            >
              ثبت خرابی
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

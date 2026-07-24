import { useEffect, useMemo, useRef, useState, type UIEvent } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  LinearProgress,
  Link,
  MenuItem,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { Cancel, CheckCircle, CheckCircleOutline, Logout, ReportProblem } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { PageHeader } from '../../components/PageHeader';
import { EmptyState, ErrorState, LoadingState } from '../../components/States';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type {
  AuthUser,
  ChecklistResult,
  FailureSeverity,
  InspectionTemplate,
  OdometerReading,
  Vehicle,
} from '../../types/fmms';
import { toFaNumber } from '../../utils/format';

type ChecklistDraft = {
  templateId: string;
  category: string;
  code: string;
  description: string;
  result: ChecklistResult | '';
  notes: string;
  severity: FailureSeverity | '';
  errors: { result?: string; notes?: string; severity?: string };
};

const SEVERITY_OPTIONS: Array<{ value: FailureSeverity; label: string }> = [
  { value: 'LOW', label: 'کم' },
  { value: 'MEDIUM', label: 'متوسط' },
  { value: 'HIGH', label: 'زیاد' },
  { value: 'CRITICAL', label: 'بحرانی' },
];

const VEHICLE_PAGE_SIZE = 20;

function mergeVehicles(current: Vehicle[], incoming: Vehicle[]): Vehicle[] {
  const seen = new Set(current.map((item) => item.id));
  return [...current, ...incoming.filter((item) => !seen.has(item.id))];
}

function isAdminUser(user: AuthUser | null): boolean {
  if (!user) return false;
  return (
    user.is_superuser ||
    user.is_staff ||
    user.role === 'ADMIN' ||
    user.role === 'SUPERVISOR'
  );
}

function normalizeTemplates(
  payload: { results?: InspectionTemplate[] } | InspectionTemplate[],
): InspectionTemplate[] {
  const items = Array.isArray(payload) ? payload : (payload.results ?? []);
  return [...items].sort(
    (a, b) =>
      a.group_text.localeCompare(b.group_text, 'fa') ||
      a.code.localeCompare(b.code, 'en', { numeric: true }),
  );
}

function hasAssignedDriver(vehicle: Vehicle): boolean {
  return Boolean(vehicle.driver1 || vehicle.driver2);
}

function DriverNameLink({
  driver,
}: {
  driver: Vehicle['driver1'];
}) {
  const label = driver?.name || driver?.customer_number || '—';
  if (!driver?.id) {
    return (
      <Typography fontWeight={700} noWrap>
        {label}
      </Typography>
    );
  }
  return (
    <Link
      component={RouterLink}
      to={`/drivers/${driver.id}`}
      underline="hover"
      fontWeight={700}
      noWrap
      display="block"
    >
      {label}
    </Link>
  );
}

function ResultToggle({
  value,
  onChange,
  size = 'small',
}: {
  value: ChecklistResult | '';
  onChange: (next: ChecklistResult) => void;
  size?: 'small' | 'medium';
}) {
  const large = size === 'medium';
  return (
    <ToggleButtonGroup
      exclusive
      size="small"
      value={value || null}
      onChange={(_event, next: ChecklistResult | null) => {
        if (next) {
          onChange(next);
          return;
        }
        // Re-selecting the active option yields null; re-fire so PASS advances again after «قبلی».
        if (value === 'PASS' || value === 'FAIL') {
          onChange(value);
        }
      }}
      sx={{
        flexShrink: 0,
        gap: 1.5,
        width: large ? '100%' : 'auto',
        '& .MuiToggleButtonGroup-grouped': {
          border: '1px solid',
          borderRadius: (t) => `${t.radius('sm')} !important`,
          px: large ? 2.5 : 1.75,
          py: large ? 1.1 : 0.5,
          flex: large ? 1 : 'initial',
          fontWeight: 800,
          fontSize: large ? '0.95rem' : '0.8rem',
          textTransform: 'none',
          gap: 0.75,
          '&:not(:first-of-type)': { ml: 0, borderRadius: (t) => `${t.radius('sm')} !important` },
          '&:first-of-type': { borderRadius: (t) => `${t.radius('sm')} !important` },
        },
      }}
    >
      <ToggleButton
        value="PASS"
        sx={{
          color: '#155f3d',
          borderColor: 'rgba(0, 167, 111, 0.35) !important',
          bgcolor: 'rgba(0, 167, 111, 0.06)',
          '&:hover': { bgcolor: 'rgba(0, 167, 111, 0.12)' },
          '&.Mui-selected': {
            bgcolor: 'rgba(0, 167, 111, 0.18)',
            borderColor: 'rgba(0, 167, 111, 0.55) !important',
            color: '#007867',
            '&:hover': { bgcolor: 'rgba(0, 167, 111, 0.24)' },
          },
        }}
      >
        <CheckCircle sx={{ fontSize: large ? 22 : 18 }} />
        سالم
      </ToggleButton>
      <ToggleButton
        value="FAIL"
        sx={{
          color: '#c94132',
          borderColor: 'rgba(201, 65, 50, 0.35) !important',
          bgcolor: 'rgba(201, 65, 50, 0.06)',
          '&:hover': { bgcolor: 'rgba(201, 65, 50, 0.12)' },
          '&.Mui-selected': {
            bgcolor: 'rgba(201, 65, 50, 0.16)',
            borderColor: 'rgba(201, 65, 50, 0.55) !important',
            color: '#9f2f27',
            '&:hover': { bgcolor: 'rgba(201, 65, 50, 0.22)' },
          },
        }}
      >
        <Cancel sx={{ fontSize: large ? 22 : 18 }} />
        خراب
      </ToggleButton>
    </ToggleButtonGroup>
  );
}

function isItemComplete(item: ChecklistDraft): boolean {
  if (!item.result) return false;
  if (item.result === 'FAIL') {
    return Boolean(item.notes.trim() && item.severity);
  }
  return true;
}

/** Keep only digits; convert Persian/Arabic numerals to ASCII. */
function digitsOnly(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(digit)))
    .replace(/\D/g, '');
}

/** Matches Django PositiveIntegerField / DB integer upper bound. */
const MAX_ODOMETER_KM = 2_147_483_647;

function todayDateIso(): string {
  const date = new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Latest odometer from a day before today (never today's reading). */
function pickPreviousOdometer(readings: OdometerReading[]): OdometerReading | null {
  if (!readings.length) return null;
  const today = todayDateIso();
  const priorDays = readings
    .filter((item) => item.reading_date.slice(0, 10) < today)
    .sort((a, b) => b.reading_date.localeCompare(a.reading_date));
  return priorDays[0] ?? null;
}

/**
 * Daily vehicle inspection flow wizard:
 * vehicle (admin) → odometer → checklist items → submit.
 */
export function InspectionPage() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [bootLoading, setBootLoading] = useState(true);
  const [bootError, setBootError] = useState('');

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [vehiclePage, setVehiclePage] = useState(1);
  const [vehicleTotal, setVehicleTotal] = useState(0);
  const [vehiclesLoadingMore, setVehiclesLoadingMore] = useState(false);
  const vehiclesLoadingRef = useRef(false);
  const vehiclePagingRef = useRef({ page: 1, total: 0, count: 0 });
  const [selectedVehicleId, setSelectedVehicleId] = useState('');
  const [flowStep, setFlowStep] = useState<'vehicle' | 'odometer' | 'checklist'>('vehicle');

  vehiclePagingRef.current = {
    page: vehiclePage,
    total: vehicleTotal,
    count: vehicles.length,
  };

  const vehicleHasMore = vehicles.length < vehicleTotal;

  const [odometer, setOdometer] = useState('');
  const [odometerError, setOdometerError] = useState('');
  const [previousOdometer, setPreviousOdometer] = useState<OdometerReading | null>(null);
  const [previousOdometerLoading, setPreviousOdometerLoading] = useState(false);
  const [odometerSaving, setOdometerSaving] = useState(false);
  const [odometerRecorded, setOdometerRecorded] = useState(false);

  const [items, setItems] = useState<ChecklistDraft[]>([]);
  const [wizardIndex, setWizardIndex] = useState(0);

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [completed, setCompleted] = useState(false);
  const [hadFailures, setHadFailures] = useState(false);
  const [completedInspection, setCompletedInspection] = useState<{ id: string; vehicle_id: string } | null>(null);
  const [actionLoading, setActionLoading] = useState<'exit' | 'fault' | ''>('');
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const admin = isAdminUser(user);
  const selectableVehicles = useMemo(
    () => (admin ? vehicles.filter(hasAssignedDriver) : vehicles),
    [admin, vehicles],
  );
  const selectedVehicle =
    selectableVehicles.find((item) => item.id === selectedVehicleId) ??
    vehicles.find((item) => item.id === selectedVehicleId) ??
    null;

  const completedCount = items.filter((item) => isItemComplete(item)).length;
  const progress = items.length ? Math.round((completedCount / items.length) * 100) : 0;
  const currentItem = items[wizardIndex] ?? null;
  const isLastItem = items.length > 0 && wizardIndex >= items.length - 1;
  const currentComplete = currentItem ? isItemComplete(currentItem) : false;
  const checklistComplete = items.length > 0 && items.every(isItemComplete);

  const odometerValid = useMemo(() => {
    const odometerValue = Number(odometer);
    return (
      Boolean(odometer.trim()) &&
      !Number.isNaN(odometerValue) &&
      odometerValue >= 0 &&
      odometerValue <= MAX_ODOMETER_KM
    );
  }, [odometer]);

  const canSubmit = useMemo(() => {
    if (!selectedVehicleId || items.length === 0 || submitting) return false;
    return odometerValid && checklistComplete;
  }, [checklistComplete, items.length, odometerValid, selectedVehicleId, submitting]);

  const assignedVehicleForDriver = useMemo(() => {
    if (admin || !user) return null;
    // Without user↔driver link, prefer a single ACTIVE vehicle if only one exists.
    const active = vehicles.filter((item) => item.status === 'ACTIVE' && hasAssignedDriver(item));
    return active.length === 1 ? active[0] : null;
  }, [admin, user, vehicles]);

  const loadVehiclesPage = async (page: number, append: boolean) => {
    if (vehiclesLoadingRef.current) return null;
    vehiclesLoadingRef.current = true;
    if (append) setVehiclesLoadingMore(true);
    try {
      const result = await api.listVehicles('', 'license_plate', {
        page,
        pageSize: VEHICLE_PAGE_SIZE,
      });
      setVehicleTotal(result.count);
      setVehiclePage(page);
      setVehicles((prev) => (append ? mergeVehicles(prev, result.results) : result.results));
      return result;
    } finally {
      vehiclesLoadingRef.current = false;
      setVehiclesLoadingMore(false);
    }
  };

  const loadMoreVehicles = () => {
    const { page, total, count } = vehiclePagingRef.current;
    if (count >= total || vehiclesLoadingRef.current) return;
    void loadVehiclesPage(page + 1, true);
  };

  const handleVehicleMenuScroll = (event: UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    if (target.scrollTop + target.clientHeight >= target.scrollHeight - 48) {
      loadMoreVehicles();
    }
  };

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      setBootLoading(true);
      setBootError('');
      try {
        const [me, vehiclePageResult, templatePayload] = await Promise.all([
          api.me(),
          api.listVehicles('', 'license_plate', { page: 1, pageSize: VEHICLE_PAGE_SIZE }),
          api.listInspectionTemplates(),
        ]);
        if (cancelled) return;
        setUser(me);
        let loadedVehicles = vehiclePageResult.results;
        let loadedTotal = vehiclePageResult.count;
        let loadedPage = 1;
        setVehicles(loadedVehicles);
        setVehicleTotal(loadedTotal);
        setVehiclePage(loadedPage);

        const nextTemplates = normalizeTemplates(templatePayload).filter((item) => item.is_active);
        setItems(
          nextTemplates.map((template) => ({
            templateId: template.id,
            category: template.group_text,
            code: template.code,
            description: template.code_text,
            result: '',
            notes: '',
            severity: '',
            errors: {},
          })),
        );
        setWizardIndex(0);

        if (isAdminUser(me)) {
          setFlowStep('vehicle');
        } else {
          const findAssigned = (list: Vehicle[]) =>
            list.filter((item) => item.status === 'ACTIVE' && hasAssignedDriver(item));

          let assigned = findAssigned(loadedVehicles);
          while (assigned.length !== 1 && loadedVehicles.length < loadedTotal) {
            loadedPage += 1;
            const next = await api.listVehicles('', 'license_plate', {
              page: loadedPage,
              pageSize: VEHICLE_PAGE_SIZE,
            });
            if (cancelled) return;
            loadedVehicles = mergeVehicles(loadedVehicles, next.results);
            loadedTotal = next.count;
            setVehicles(loadedVehicles);
            setVehicleTotal(loadedTotal);
            setVehiclePage(loadedPage);
            assigned = findAssigned(loadedVehicles);
          }

          if (assigned.length === 1) {
            setSelectedVehicleId(assigned[0].id);
            setFlowStep('odometer');
          }
        }
      } catch (err) {
        if (!cancelled) {
          setBootError(err instanceof Error ? err.message : 'خطا در آماده‌سازی فرم بازرسی');
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

  useEffect(() => {
    if (!admin && assignedVehicleForDriver) {
      setSelectedVehicleId(assignedVehicleForDriver.id);
      setFlowStep('odometer');
    }
  }, [admin, assignedVehicleForDriver]);

  useEffect(() => {
    if (!selectedVehicleId) {
      setPreviousOdometer(null);
      return;
    }

    let cancelled = false;
    setPreviousOdometerLoading(true);
    void api
      .getOdometerHistory(selectedVehicleId)
      .then((readings) => {
        if (!cancelled) setPreviousOdometer(pickPreviousOdometer(readings));
      })
      .catch(() => {
        if (!cancelled) setPreviousOdometer(null);
      })
      .finally(() => {
        if (!cancelled) setPreviousOdometerLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedVehicleId]);

  const updateItem = (index: number, patch: Partial<ChecklistDraft>) => {
    setItems((current) =>
      current.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              ...patch,
              errors: {},
            }
          : item,
      ),
    );
  };

  const goNext = () => {
    setWizardIndex((current) => Math.min(current + 1, Math.max(items.length - 1, 0)));
  };

  const goPrev = () => {
    setWizardIndex((current) => Math.max(current - 1, 0));
  };

  const handleResultChange = (next: ChecklistResult) => {
    if (!currentItem) return;
    updateItem(wizardIndex, {
      result: next,
      notes: next === 'FAIL' ? currentItem.notes : '',
      severity: next === 'FAIL' ? currentItem.severity : '',
    });
    if (next === 'PASS' && !isLastItem) {
      // Advance after PASS so the driver sees one item at a time.
      window.setTimeout(() => {
        setWizardIndex((current) => Math.min(current + 1, Math.max(items.length - 1, 0)));
      }, 180);
    }
  };

  const validateCurrentItem = (): boolean => {
    if (!currentItem) return false;
    const errors: ChecklistDraft['errors'] = {};
    if (!currentItem.result) {
      errors.result = 'وضعیت الزامی است';
    }
    if (currentItem.result === 'FAIL') {
      if (!currentItem.notes.trim()) errors.notes = 'شرح خرابی الزامی است';
      if (!currentItem.severity) errors.severity = 'شدت خرابی الزامی است';
    }
    if (Object.keys(errors).length) {
      updateItem(wizardIndex, { errors });
      return false;
    }
    return true;
  };

  const handleNext = () => {
    if (!validateCurrentItem()) return;
    if (!isLastItem) goNext();
  };

  const validate = (): boolean => {
    let ok = true;
    if (!selectedVehicleId) ok = false;
    if (!odometer.trim() || Number.isNaN(Number(odometer)) || Number(odometer) < 0) {
      setOdometerError('مقدار کیلومتر معتبر الزامی است');
      ok = false;
    } else {
      setOdometerError('');
    }

    setItems((current) =>
      current.map((item) => {
        const errors: ChecklistDraft['errors'] = {};
        if (!item.result) {
          errors.result = 'وضعیت الزامی است';
          ok = false;
        }
        if (item.result === 'FAIL') {
          if (!item.notes.trim()) {
            errors.notes = 'شرح خرابی الزامی است';
            ok = false;
          }
          if (!item.severity) {
            errors.severity = 'شدت خرابی الزامی است';
            ok = false;
          }
        }
        return { ...item, errors };
      }),
    );
    return ok;
  };

  const submit = async () => {
    if (!validate() || !selectedVehicleId) return;
    setSubmitting(true);
    setSubmitError('');
    try {
      const payloadItems = items.map((item) => ({
        category: item.category,
        description: item.description,
        result: item.result as ChecklistResult,
        notes: item.result === 'FAIL' ? item.notes : null,
        severity: item.result === 'FAIL' ? (item.severity as FailureSeverity) : null,
      }));

      const created = await api.createInspection({
        vehicle_id: selectedVehicleId,
        inspection_type: 'PRE_TRIP',
        odometer_value: Number(odometer),
        odometer_unit: 'KM',
        inspected_at: new Date().toISOString(),
        driver_id: selectedVehicle?.driver1?.id || selectedVehicle?.driver2?.id || null,
        items: payloadItems,
      });
      const submitted = await api.submitInspection(created.id);
      setHadFailures(Boolean(submitted.has_failures));
      setCompletedInspection({ id: submitted.id, vehicle_id: submitted.vehicle_id });
      setActionError('');
      setActionSuccess('');
      setCompleted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'ثبت بازرسی انجام نشد');
    } finally {
      setSubmitting(false);
    }
  };

  const selectedDriverIdForExit = selectedVehicle?.driver1?.id || selectedVehicle?.driver2?.id || '';

  const handleExitCenter = async () => {
    if (!completedInspection || !selectedDriverIdForExit) return;
    setActionLoading('exit');
    setActionError('');
    setActionSuccess('');
    try {
      await api.driverExitCenter(selectedDriverIdForExit, {
        vehicle_id: completedInspection.vehicle_id,
        inspection_id: completedInspection.id,
      });
      setActionSuccess('خروج خودرو از مرکز ثبت شد.');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'ثبت خروج از مرکز انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const handleReportFault = async () => {
    if (!completedInspection) return;
    setActionLoading('fault');
    setActionError('');
    setActionSuccess('');
    try {
      await api.reportInspectionFault(completedInspection.id);
      setActionSuccess('خرابی چک‌لیست ثبت شد و دستور تعمیر ایجاد شد.');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'اعلام خرابی انجام نشد');
    } finally {
      setActionLoading('');
    }
  };

  const validateOdometerStep = (): boolean => {
    if (!odometer.trim() || Number.isNaN(Number(odometer)) || Number(odometer) < 0) {
      setOdometerError('مقدار کیلومتر معتبر الزامی است');
      return false;
    }
    if (Number(odometer) > MAX_ODOMETER_KM) {
      setOdometerError(`حداکثر مقدار کیلومتر ${toFaNumber(MAX_ODOMETER_KM)} است`);
      return false;
    }
    if (previousOdometer && Number(odometer) < previousOdometer.odometer_km) {
      setOdometerError(
        `مقدار کیلومتر نمی‌تواند کمتر از کیلومتر قبلی (${toFaNumber(previousOdometer.odometer_km)}) باشد`,
      );
      return false;
    }
    setOdometerError('');
    return true;
  };

  const goToOdometer = () => {
    if (!selectedVehicleId) return;
    setWizardIndex(0);
    setFlowStep('odometer');
  };

  const goToChecklist = async () => {
    if (!validateOdometerStep() || !selectedVehicleId) return;

    if (odometerRecorded) {
      setWizardIndex(0);
      setFlowStep('checklist');
      return;
    }

    setOdometerSaving(true);
    setOdometerError('');
    try {
      const today = todayDateIso();
      await api.recordOdometer(selectedVehicleId, {
        reading_date: today,
        odometer_km: Number(odometer),
      });
      setOdometerRecorded(true);
      setWizardIndex(0);
      setFlowStep('checklist');
    } catch (err) {
      setOdometerError(err instanceof Error ? err.message : 'ثبت کیلومتر انجام نشد');
    } finally {
      setOdometerSaving(false);
    }
  };

  const stepLabels = admin
    ? [
        { key: 'vehicle', label: 'انتخاب خودرو' },
        { key: 'odometer', label: 'کیلومتر' },
        { key: 'checklist', label: 'چک‌لیست' },
      ]
    : [
        { key: 'odometer', label: 'کیلومتر' },
        { key: 'checklist', label: 'چک‌لیست' },
      ];

  const vehicleSummary = selectedVehicle ? (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 1.25,
        px: 1.5,
        py: 1.35,
        borderRadius: (t) => t.radius('md'),
        bgcolor: 'rgba(0, 167, 111, 0.04)',
        border: '1px solid rgba(0, 167, 111, 0.14)',
      }}
    >
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          پلاک
        </Typography>
        <Link
          component={RouterLink}
          to={`/vehicles?vehicleId=${encodeURIComponent(selectedVehicle.id)}`}
          underline="hover"
          fontWeight={800}
          display="block"
        >
          {selectedVehicle.license_plate}
        </Link>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          شناسه خودرو
        </Typography>
        <Typography fontWeight={800}>{selectedVehicle.vehicle_number}</Typography>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          راننده اصلی
        </Typography>
        <DriverNameLink driver={selectedVehicle.driver1} />
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" fontWeight={700}>
          کمک راننده
        </Typography>
        <DriverNameLink driver={selectedVehicle.driver2} />
      </Box>
    </Box>
  ) : null;

  if (bootLoading) return <LoadingState label="در حال آماده‌سازی بازرسی روزانه" />;
  if (bootError) return <ErrorState message={bootError} onRetry={() => window.location.reload()} />;

  if (!admin && !assignedVehicleForDriver) {
    return (
      <Stack spacing={2} style={{ direction: 'rtl', textAlign: 'right' }}>
        <PageHeader
          title="بازرسی روزانه خودرو"
          breadcrumbs={[
            { label: 'مدیریت ناوگان', to: '/vehicles' },
            { label: 'بازرسی روزانه' },
          ]}
        />
        <EmptyState
          title="در حال حاضر هیچ خودرویی به شما تخصیص داده نشده است."
          subtitle="پس از تخصیص خودرو توسط سامانه، امکان ثبت بازرسی فعال می‌شود."
        />
      </Stack>
    );
  }

  if (completed) {
    return (
      <Stack spacing={{ xs: 1.5, md: 2 }} style={{ direction: 'rtl', textAlign: 'right' }}>
        <PageHeader
          title="بازرسی روزانه خودرو"
          breadcrumbs={[
            { label: 'مدیریت ناوگان', to: '/vehicles' },
            { label: 'بازرسی روزانه' },
          ]}
        />

        <Card
          variant="outlined"
          sx={{
            width: '100%',
            borderColor: 'rgba(184, 197, 188, 0.9)',
            borderRadius: (t) => t.radius('md'),
            boxShadow: '0 8px 24px rgba(31, 79, 57, 0.05)',
            bgcolor: 'background.paper',
            overflow: 'hidden',
          }}
        >
          <CardContent
            sx={{
              p: { xs: 1.75, sm: 2.25, md: 2.5 },
              '&:last-child': { pb: { xs: 1.75, sm: 2.25, md: 2.5 } },
            }}
          >
            <Stack spacing={2.25} alignItems="center">
              <Box
                sx={{
                  px: 1.5,
                  py: 0.65,
                  borderRadius: (t) => t.radius('sm'),
                  fontSize: '0.8rem',
                  fontWeight: 800,
                  color: 'primary.dark',
                  bgcolor: 'rgba(0, 167, 111, 0.12)',
                  border: '1px solid',
                  borderColor: 'rgba(0, 167, 111, 0.35)',
                }}
              >
                تکمیل بازرسی
              </Box>

              <Box
                sx={{
                  width: '100%',
                  maxWidth: 640,
                  mx: 'auto',
                  p: { xs: 2.5, sm: 3.5 },
                  borderRadius: (t) => t.radius('md'),
                  border: '1px solid',
                  borderColor: 'divider',
                  bgcolor: 'background.default',
                  textAlign: 'center',
                }}
              >
                <CheckCircleOutline color="success" sx={{ fontSize: 64, mb: 1.5 }} />
                <Typography variant="h2" mb={1}>
                  بازرسی با موفقیت ثبت شد
                </Typography>
                <Typography color="text.secondary" mb={2.5}>
                  {hadFailures
                    ? 'در صورت نیاز اعلام خرابی کنید.'
                    : 'تمام موارد چک‌لیست بدون خرابی ثبت شد.'}
                </Typography>
                <Stack
                  direction={{ xs: 'column', sm: 'row' }}
                  useFlexGap
                  justifyContent="center"
                  alignItems="center"
                  sx={{ gap: 2, '& > *': { margin: 0 } }}
                >
                  {hadFailures && (
                    <Button
                      variant="contained"
                      color="error"
                      size="large"
                      startIcon={<ReportProblem />}
                      onClick={handleReportFault}
                      loading={actionLoading === 'fault'}
                      disabled={actionLoading !== ''}
                    >
                      اعلام خرابی
                    </Button>
                  )}
                  <Button
                    variant={hadFailures ? 'outlined' : 'contained'}
                    size="large"
                    startIcon={<Logout />}
                    onClick={handleExitCenter}
                    loading={actionLoading === 'exit'}
                    disabled={actionLoading !== '' || !selectedDriverIdForExit}
                  >
                    اقدام به خروج
                  </Button>
                </Stack>
                {actionError && (
                  <Alert severity="error" sx={{ mt: 2, textAlign: 'right' }}>
                    {actionError}
                  </Alert>
                )}
                {actionSuccess && (
                  <Alert severity="success" sx={{ mt: 2, textAlign: 'right' }}>
                    {actionSuccess}
                  </Alert>
                )}
                {hadFailures && (
                  <Typography variant="caption" color="text.secondary" display="block" mt={1.25}>
                    اگر خرابی جزئی است و نیازی به خروج از سرویس نیست، می‌توانید مستقیم اقدام به خروج کنید.
                  </Typography>
                )}
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    );
  }

  return (
    <Stack spacing={{ xs: 1.5, md: 2 }} style={{ direction: 'rtl', textAlign: 'right' }}>
      <PageHeader
        title="بازرسی روزانه خودرو"
        breadcrumbs={[
          { label: 'مدیریت ناوگان', to: '/vehicles' },
          { label: 'بازرسی روزانه' },
        ]}
      />

      <Card
        variant="outlined"
        sx={{
          width: '100%',
          borderColor: 'rgba(184, 197, 188, 0.9)',
          borderRadius: (t) => t.radius('md'),
          boxShadow: '0 8px 24px rgba(31, 79, 57, 0.05)',
          bgcolor: 'background.paper',
          overflow: 'hidden',
        }}
      >
        <CardContent
          sx={{
            p: { xs: 1.75, sm: 2.25, md: 2.5 },
            '&:last-child': { pb: { xs: 1.75, sm: 2.25, md: 2.5 } },
          }}
        >
          <Stack spacing={2.25} alignItems="center">
            <Stack direction="row" gap={1} flexWrap="wrap" justifyContent="center" width="100%">
              {stepLabels.map((step) => {
                const active = flowStep === step.key;
                return (
                  <Box
                    key={step.key}
                    sx={{
                      px: 1.5,
                      py: 0.65,
                      borderRadius: (t) => t.radius('sm'),
                      fontSize: '0.8rem',
                      fontWeight: active ? 800 : 650,
                      color: active ? 'primary.dark' : 'text.secondary',
                      bgcolor: active ? 'rgba(0, 167, 111, 0.12)' : 'rgba(145, 158, 171, 0.1)',
                      border: '1px solid',
                      borderColor: active ? 'rgba(0, 167, 111, 0.35)' : 'transparent',
                    }}
                  >
                    {step.label}
                  </Box>
                );
              })}
            </Stack>

            <Box
              sx={{
                width: '100%',
                maxWidth: 640,
                mx: 'auto',
                p: { xs: 1.5, sm: 2 },
                borderRadius: (t) => t.radius('md'),
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: 'background.default',
              }}
            >
                {flowStep === 'vehicle' && (
                  <Stack spacing={2}>
                    <Typography fontWeight={800}>انتخاب خودرو</Typography>
                    <RtlSelectField
                      label="خودرو"
                      value={selectedVehicleId}
                      displayEmpty
                      onChange={(event) => {
                        setSelectedVehicleId(String(event.target.value));
                        setWizardIndex(0);
                        setOdometer('');
                        setOdometerError('');
                        setOdometerRecorded(false);
                      }}
                      fullWidth
                      MenuProps={{
                        PaperProps: {
                          onScroll: handleVehicleMenuScroll,
                          sx: { maxHeight: 260 },
                        },
                      }}
                    >
                      <MenuItem value="">
                        <em>انتخاب خودرو دارای راننده</em>
                      </MenuItem>
                      {selectableVehicles.map((vehicle) => (
                        <MenuItem key={vehicle.id} value={vehicle.id}>
                          {vehicle.license_plate} — {vehicle.vehicle_number}
                        </MenuItem>
                      ))}
                      {(vehiclesLoadingMore || vehicleHasMore) && (
                        <MenuItem disabled value="__loading__" sx={{ justifyContent: 'center', opacity: 1 }}>
                          {vehiclesLoadingMore ? (
                            <CircularProgress size={18} />
                          ) : (
                            <Typography variant="caption" color="text.secondary">
                              برای موارد بیشتر اسکرول کنید
                            </Typography>
                          )}
                        </MenuItem>
                      )}
                    </RtlSelectField>
                    {!selectableVehicles.length && (
                      <Typography variant="body2" color="text.secondary">
                        خودرویی با راننده تخصیص‌یافته یافت نشد.
                      </Typography>
                    )}
                    {vehicleSummary}
                    <Stack direction="row" justifyContent="flex-end">
                      <Button variant="contained" disabled={!selectedVehicleId} onClick={goToOdometer}>
                        ادامه
                      </Button>
                    </Stack>
                  </Stack>
                )}

                {flowStep === 'odometer' && (
                  <Stack spacing={2}>
                    <Typography fontWeight={800}>ثبت کیلومتر</Typography>
                    {vehicleSummary}
                    <RtlTextField
                      label="مقدار کیلومتر"
                      value={odometer}
                      onChange={(event) => {
                        setOdometerRecorded(false);
                        setOdometer(digitsOnly(event.target.value).slice(0, 10));
                      }}
                      onKeyDown={(event) => {
                        if (
                          event.key.length === 1 &&
                          !/[0-9۰-۹٠-٩]/.test(event.key) &&
                          !event.ctrlKey &&
                          !event.metaKey
                        ) {
                          event.preventDefault();
                        }
                      }}
                      error={Boolean(odometerError)}
                      helperText={
                        odometerError ||
                        (previousOdometerLoading
                          ? 'در حال دریافت کیلومتر قبلی...'
                          : previousOdometer
                            ? `آخرین کیلومتر قبل از امروز: ${toFaNumber(previousOdometer.odometer_km)} KM`
                            : selectedVehicleId
                              ? 'کیلومتر روزهای قبل ثبت نشده است'
                              : 'فقط عدد وارد کنید')
                      }
                      inputProps={{
                        inputMode: 'numeric',
                        pattern: '[0-9]*',
                        autoComplete: 'off',
                      }}
                      fullWidth
                      disabled={odometerSaving}
                    />
                    <Stack direction="row" justifyContent="space-between">
                      {admin ? (
                        <Button
                          variant="outlined"
                          disabled={odometerSaving}
                          onClick={() => setFlowStep('vehicle')}
                        >
                          قبلی
                        </Button>
                      ) : (
                        <Box />
                      )}
                      <Button
                        variant="contained"
                        disabled={!odometerValid || odometerSaving}
                        onClick={() => void goToChecklist()}
                      >
                        {odometerSaving ? 'در حال ثبت کیلومتر...' : 'ادامه به چک‌لیست'}
                      </Button>
                    </Stack>
                  </Stack>
                )}

                {flowStep === 'checklist' && (
                  <Stack spacing={2}>
                    <Stack
                      direction={{ xs: 'column', sm: 'row' }}
                      justifyContent="space-between"
                      alignItems={{ xs: 'stretch', sm: 'center' }}
                      gap={1}
                    >
                      <Typography fontWeight={800}>چک‌لیست روزانه</Typography>
                      <Typography variant="body2" color="text.secondary">
                        مورد {toFaNumber(items.length ? wizardIndex + 1 : 0)} از{' '}
                        {toFaNumber(items.length)}
                        {completedCount > 0 ? ` · ${toFaNumber(completedCount)} تکمیل‌شده` : ''}
                      </Typography>
                    </Stack>

                    {vehicleSummary}

                    <LinearProgress
                      variant="determinate"
                      value={progress}
                      sx={{
                        height: 6,
                        borderRadius: 1,
                        bgcolor: 'rgba(145, 158, 171, 0.16)',
                        '& .MuiLinearProgress-bar': { borderRadius: 1 },
                      }}
                    />

                    {!items.length && (
                      <EmptyState
                        title="آیتم چک‌لیستی یافت نشد"
                        subtitle="ابتدا قالب‌های بازرسی را از SAP همگام‌سازی کنید."
                      />
                    )}

                    {currentItem && (
                      <Box
                        sx={{
                          p: { xs: 1.75, sm: 2 },
                          border: '1px solid',
                          borderColor:
                            currentItem.errors.result ||
                            currentItem.errors.notes ||
                            currentItem.errors.severity
                              ? 'error.light'
                              : 'divider',
                          borderRadius: (t) => t.radius('md'),
                          bgcolor: 'background.paper',
                        }}
                        >
                        <Stack
                          direction="row"
                          spacing={1}
                          justifyContent="space-between"
                          alignItems="center"
                          mb={1.25}
                          sx={{
                            px: 1.25,
                            py: 0.75,
                            borderRadius: (t) => t.radius('sm'),
                            bgcolor: 'rgba(0, 167, 111, 0.06)',
                            border: '1px solid rgba(0, 167, 111, 0.16)',
                          }}
                        >
                          <Typography variant="body2" color="primary.main" fontWeight={900}>
                            {currentItem.category}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            fontWeight={900}
                            sx={{
                              direction: 'ltr',
                              px: 0.75,
                              py: 0.25,
                              borderRadius: 1,
                              bgcolor: 'background.paper',
                              border: '1px solid',
                              borderColor: 'divider',
                            }}
                          >
                            {currentItem.code}
                          </Typography>
                        </Stack>
                        <Typography
                          fontWeight={800}
                          fontSize={{ xs: '1.05rem', sm: '1.15rem' }}
                          mb={2}
                          textAlign="center"
                        >
                          {currentItem.description}
                        </Typography>

                        <ResultToggle
                          size="medium"
                          value={currentItem.result}
                          onChange={handleResultChange}
                        />

                        {currentItem.errors.result && (
                          <Typography
                            variant="caption"
                            color="error.main"
                            display="block"
                            mt={1}
                            textAlign="center"
                          >
                            {currentItem.errors.result}
                          </Typography>
                        )}

                        {currentItem.result === 'FAIL' && (
                          <Stack spacing={1.5} mt={2.25}>
                            <Alert severity="warning" sx={{ py: 0.5 }}>
                              برای ادامه، شرح و شدت خرابی را وارد کنید.
                            </Alert>
                            <RtlSelectField
                              label="شدت خرابی"
                              value={currentItem.severity}
                              displayEmpty
                              onChange={(event) =>
                                updateItem(wizardIndex, {
                                  severity: event.target.value as FailureSeverity,
                                })
                              }
                              error={Boolean(currentItem.errors.severity)}
                              fullWidth
                            >
                              <MenuItem value="">
                                <em>انتخاب شدت</em>
                              </MenuItem>
                              {SEVERITY_OPTIONS.map((option) => (
                                <MenuItem key={option.value} value={option.value}>
                                  {option.label}
                                </MenuItem>
                              ))}
                            </RtlSelectField>
                            {currentItem.errors.severity && (
                              <Typography variant="caption" color="error.main">
                                {currentItem.errors.severity}
                              </Typography>
                            )}
                            <RtlTextField
                              label="شرح خرابی"
                              value={currentItem.notes}
                              onChange={(event) =>
                                updateItem(wizardIndex, { notes: event.target.value })
                              }
                              multiline
                              minRows={3}
                              error={Boolean(currentItem.errors.notes)}
                              helperText={currentItem.errors.notes}
                              fullWidth
                            />
                          </Stack>
                        )}

                        <Stack
                          direction="row"
                          justifyContent="space-between"
                          alignItems="center"
                          gap={1.25}
                          mt={2.5}
                        >
                          <Button
                            variant="outlined"
                            onClick={() => {
                              if (wizardIndex === 0) setFlowStep('odometer');
                              else goPrev();
                            }}
                          >
                            قبلی
                          </Button>

                          {!isLastItem ? (
                            <Button
                              variant="contained"
                              disabled={!currentComplete}
                              onClick={handleNext}
                            >
                              مورد بعدی
                            </Button>
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              {checklistComplete
                                ? 'چک‌لیست کامل شد'
                                : currentItem.result === 'FAIL'
                                  ? 'شرح و شدت را تکمیل کنید'
                                  : 'وضعیت این مورد را مشخص کنید'}
                            </Typography>
                          )}
                        </Stack>
                      </Box>
                    )}

                    {submitError && isLastItem && <Alert severity="error">{submitError}</Alert>}

                    {isLastItem && (
                      <Stack direction="row" justifyContent="flex-end" pt={0.5}>
                        <Button
                          variant="contained"
                          size="large"
                          disabled={!canSubmit}
                          onClick={() => void submit()}
                        >
                          {submitting ? 'در حال ثبت...' : 'ثبت و ارسال بازرسی'}
                        </Button>
                      </Stack>
                    )}
                  </Stack>
                )}
              </Box>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

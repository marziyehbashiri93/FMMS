import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Link,
  MenuItem,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { CheckCircleOutline } from '@mui/icons-material';
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
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
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
        if (next) onChange(next);
      }}
      sx={{
        flexShrink: 0,
        gap: 1,
        width: large ? '100%' : 'auto',
        '& .MuiToggleButtonGroup-grouped': {
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: (t) => `${t.radius('sm')} !important`,
          px: large ? 2.5 : 1.75,
          py: large ? 1 : 0.35,
          flex: large ? 1 : 'initial',
          fontWeight: 800,
          fontSize: large ? '0.95rem' : '0.8rem',
          color: 'text.secondary',
          bgcolor: 'background.paper',
          textTransform: 'none',
          '&:not(:first-of-type)': { ml: 0, borderRadius: (t) => `${t.radius('sm')} !important` },
          '&:first-of-type': { borderRadius: (t) => `${t.radius('sm')} !important` },
        },
      }}
    >
      <ToggleButton
        value="PASS"
        sx={{
          '&.Mui-selected': {
            bgcolor: 'rgba(0, 167, 111, 0.12)',
            borderColor: 'rgba(0, 167, 111, 0.45) !important',
            color: 'primary.dark',
            '&:hover': { bgcolor: 'rgba(0, 167, 111, 0.18)' },
          },
        }}
      >
        قبول
      </ToggleButton>
      <ToggleButton
        value="FAIL"
        sx={{
          '&.Mui-selected': {
            bgcolor: 'rgba(159, 47, 39, 0.1)',
            borderColor: 'rgba(159, 47, 39, 0.45) !important',
            color: '#9f2f27',
            '&:hover': { bgcolor: 'rgba(159, 47, 39, 0.16)' },
          },
        }}
      >
        رد
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

function yesterdayDateIso(): string {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/** Prefer yesterday's reading; otherwise fall back to the latest recorded value. */
function pickPreviousOdometer(readings: OdometerReading[]): OdometerReading | null {
  if (!readings.length) return null;
  const yesterday = yesterdayDateIso();
  return readings.find((item) => item.reading_date.slice(0, 10) === yesterday) ?? readings[0];
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
  const [selectedVehicleId, setSelectedVehicleId] = useState('');
  const [flowStep, setFlowStep] = useState<'vehicle' | 'odometer' | 'checklist'>('vehicle');

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
    return Boolean(odometer.trim()) && !Number.isNaN(odometerValue) && odometerValue >= 0;
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

  useEffect(() => {
    let cancelled = false;
    const boot = async () => {
      setBootLoading(true);
      setBootError('');
      try {
        const [me, vehiclePage, templatePayload] = await Promise.all([
          api.me(),
          api.listVehicles(''),
          api.listInspectionTemplates(),
        ]);
        if (cancelled) return;
        setUser(me);
        setVehicles(vehiclePage.results);
        const nextTemplates = normalizeTemplates(templatePayload).filter((item) => item.is_active);
        setItems(
          nextTemplates.map((template) => ({
            templateId: template.id,
            category: template.category || template.description,
            description: template.description,
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
          const assigned = vehiclePage.results.filter(
            (item) => item.status === 'ACTIVE' && hasAssignedDriver(item),
          );
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
      setCompleted(true);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'ثبت بازرسی انجام نشد');
    } finally {
      setSubmitting(false);
    }
  };

  const validateOdometerStep = (): boolean => {
    if (!odometerValid) {
      setOdometerError('مقدار کیلومتر معتبر الزامی است');
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
      const today = new Date().toISOString().slice(0, 10);
      const recorded = await api.recordOdometer(selectedVehicleId, {
        reading_date: today,
        odometer_km: Number(odometer),
      });
      setPreviousOdometer(recorded);
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
                    ? 'حداقل یک مورد خرابی ثبت شده و ادامه فرآیند توسط سامانه انجام می‌شود.'
                    : 'تمام موارد چک‌لیست بدون خرابی ثبت شد.'}
                </Typography>
                <Button variant="contained" size="large" disabled>
                  اقدام به خروج
                </Button>
                <Typography variant="caption" color="text.secondary" display="block" mt={1.25}>
                  این اقدام به‌زودی از سمت Backend فعال می‌شود.
                </Typography>
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
                    >
                      <MenuItem value="">
                        <em>انتخاب خودرو دارای راننده</em>
                      </MenuItem>
                      {selectableVehicles.map((vehicle) => (
                        <MenuItem key={vehicle.id} value={vehicle.id}>
                          {vehicle.license_plate} — {vehicle.vehicle_number}
                        </MenuItem>
                      ))}
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
                        setOdometer(digitsOnly(event.target.value));
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
                          ? 'در حال دریافت کیلومتر دیروز...'
                          : previousOdometer
                            ? `کیلومتر دیروز: ${toFaNumber(previousOdometer.odometer_km)} KM`
                            : selectedVehicleId
                              ? 'کیلومتر دیروز ثبت نشده است'
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

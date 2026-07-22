import { useState } from 'react';
import {
  Alert,
  Box,
  Card,
  CardContent,
  MenuItem,
  Stack,
  Typography,
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { Button } from '../../components/Button';
import { PageHeader } from '../../components/PageHeader';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { FailureSeverity } from '../../types/fmms';

const SEVERITY_OPTIONS: Array<{ value: FailureSeverity; label: string }> = [
  { value: 'LOW', label: 'کم' },
  { value: 'MEDIUM', label: 'متوسط' },
  { value: 'HIGH', label: 'زیاد' },
  { value: 'CRITICAL', label: 'بحرانی' },
];

const CATEGORY_OPTIONS = [
  'موتور',
  'ترمز',
  'چرخ و لاستیک',
  'برق و باتری',
  'بدنه',
  'سایر',
];

/**
 * Manual fault registration UI (no API yet).
 */
export function ManualFaultPage() {
  const [vehicle, setVehicle] = useState('');
  const [category, setCategory] = useState('');
  const [severity, setSeverity] = useState<FailureSeverity | ''>('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const next: Record<string, string> = {};
    if (!vehicle.trim()) next.vehicle = 'انتخاب خودرو الزامی است';
    if (!category) next.category = 'دسته‌بندی الزامی است';
    if (!severity) next.severity = 'شدت خرابی الزامی است';
    if (!title.trim()) next.title = 'عنوان خرابی الزامی است';
    if (!description.trim()) next.description = 'شرح خرابی الزامی است';
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const submit = () => {
    setSuccess(false);
    if (!validate()) return;
    setSuccess(true);
  };

  return (
    <Stack spacing={{ xs: 1.5, md: 2.25 }} style={{ direction: 'rtl', textAlign: 'right' }} maxWidth={720}>
      <PageHeader
        title="ثبت خرابی موردی"
        description="ثبت خرابی مستقل از بازرسی روزانه (فعلاً فقط رابط کاربری)"
        breadcrumbs={[
          { label: 'مدیریت ناوگان', to: '/vehicles' },
          { label: 'ثبت خرابی' },
        ]}
      />

      <Card>
        <CardContent sx={{ p: { xs: 1.75, md: 2.25 }, display: 'grid', gap: 1.75 }}>
          <RtlTextField
            label="خودرو"
            value={vehicle}
            onChange={(event) => setVehicle(event.target.value)}
            placeholder="پلاک یا شناسه خودرو"
            error={Boolean(errors.vehicle)}
            helperText={errors.vehicle}
          />

          <RtlSelectField
            label="دسته‌بندی خرابی"
            value={category}
            displayEmpty
            onChange={(event) => setCategory(String(event.target.value))}
            error={Boolean(errors.category)}
          >
            <MenuItem value="">
              <em>انتخاب دسته‌بندی</em>
            </MenuItem>
            {CATEGORY_OPTIONS.map((item) => (
              <MenuItem key={item} value={item}>
                {item}
              </MenuItem>
            ))}
          </RtlSelectField>
          {errors.category && (
            <Typography variant="caption" color="error.main">
              {errors.category}
            </Typography>
          )}

          <RtlSelectField
            label="شدت خرابی"
            value={severity}
            displayEmpty
            onChange={(event) => setSeverity(event.target.value as FailureSeverity)}
            error={Boolean(errors.severity)}
          >
            <MenuItem value="">
              <em>انتخاب شدت</em>
            </MenuItem>
            {SEVERITY_OPTIONS.map((item) => (
              <MenuItem key={item.value} value={item.value}>
                {item.label}
              </MenuItem>
            ))}
          </RtlSelectField>
          {errors.severity && (
            <Typography variant="caption" color="error.main">
              {errors.severity}
            </Typography>
          )}

          <RtlTextField
            label="عنوان خرابی"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            error={Boolean(errors.title)}
            helperText={errors.title}
          />

          <RtlTextField
            label="شرح خرابی"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            multiline
            minRows={4}
            error={Boolean(errors.description)}
            helperText={errors.description}
          />

          <Box
            sx={{
              border: '1px dashed',
              borderColor: 'divider',
              borderRadius: (t) => t.radius('md'),
              bgcolor: 'rgba(244, 246, 248, 0.9)',
              p: 3,
              textAlign: 'center',
            }}
          >
            <CloudUpload color="disabled" sx={{ fontSize: 36, mb: 1 }} />
            <Typography fontWeight={700} mb={0.5}>
              آپلود تصاویر
            </Typography>
            <Typography variant="body2" color="text.secondary">
              این بخش به‌زودی فعال می‌شود (Placeholder)
            </Typography>
          </Box>

          {success && (
            <Alert severity="success">
              فرم معتبر است. اتصال API ثبت خرابی هنوز پیاده‌سازی نشده است.
            </Alert>
          )}

          <Stack direction="row" justifyContent="flex-start">
            <Button variant="contained" onClick={submit}>
              ثبت خرابی
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}

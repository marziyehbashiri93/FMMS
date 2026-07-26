import { Chip } from '@mui/material';
import type { VehicleStatus } from '../types/fmms';

type BadgeAppearance = 'soft' | 'solid';

const statusStyles: Record<VehicleStatus, { bg: string; softBg: string; border: string; label: string }> = {
  ACTIVE: { bg: '#248a57', softBg: 'rgba(36, 138, 87, 0.12)', border: 'rgba(36, 138, 87, 0.35)', label: 'عملیاتی' },
  INACTIVE: { bg: '#647067', softBg: 'rgba(100, 112, 103, 0.12)', border: 'rgba(100, 112, 103, 0.35)', label: 'غیرفعال' },
  UNDER_REPAIR: { bg: '#d28a20', softBg: 'rgba(210, 138, 32, 0.14)', border: 'rgba(210, 138, 32, 0.42)', label: 'در تعمیر' },
  UNDER_EXTERNAL_REPAIR: { bg: '#9a5b14', softBg: 'rgba(154, 91, 20, 0.14)', border: 'rgba(154, 91, 20, 0.38)', label: 'در تعمیرگاه بیرونی' },
  WAITING_DRIVER_CONFIRMATION: { bg: '#2d6f95', softBg: 'rgba(45, 111, 149, 0.12)', border: 'rgba(45, 111, 149, 0.36)', label: 'منتظر تایید راننده' },
  EXITED_CENTER: { bg: '#0F6B4C', softBg: 'rgba(15, 107, 76, 0.12)', border: 'rgba(15, 107, 76, 0.36)', label: 'خارج شده از مرکز' },
  SUSPENDED: { bg: '#647067', softBg: 'rgba(100, 112, 103, 0.12)', border: 'rgba(100, 112, 103, 0.35)', label: 'تعلیق‌شده' },
  OUT_OF_SERVICE: { bg: '#c94132', softBg: 'rgba(201, 65, 50, 0.12)', border: 'rgba(201, 65, 50, 0.36)', label: 'خارج از سرویس' },
  DECOMMISSIONED: { bg: '#9f2f27', softBg: 'rgba(159, 47, 39, 0.12)', border: 'rgba(159, 47, 39, 0.36)', label: 'از رده خارج' },
};

export function VehicleStatusBadge({
  status,
  label,
  appearance = 'soft',
}: {
  status: VehicleStatus;
  label?: string;
  appearance?: BadgeAppearance;
}) {
  const config = statusStyles[status] ?? statusStyles.INACTIVE;
  return (
    <Chip
      size="small"
      label={label || config.label}
      sx={{
        minWidth: 76,
        bgcolor: appearance === 'solid' ? config.bg : config.softBg,
        color: appearance === 'solid' ? '#ffffff' : config.bg,
        border: '1px solid',
        borderColor: appearance === 'solid' ? config.bg : config.border,
        '& .MuiChip-label': { px: 1 },
      }}
    />
  );
}

export function PlainStatusBadge({
  label,
  appearance = 'soft',
  tone = 'success',
}: {
  label: string;
  appearance?: BadgeAppearance;
  tone?: 'success' | 'error' | 'warning' | 'neutral';
}) {
  const palette = {
    success: {
      solid: '#155f3d',
      softBg: 'rgba(21, 95, 61, 0.1)',
      softFg: '#155f3d',
      border: 'rgba(21, 95, 61, 0.28)',
    },
    error: {
      solid: '#c94132',
      softBg: 'rgba(201, 65, 50, 0.12)',
      softFg: '#c94132',
      border: 'rgba(201, 65, 50, 0.36)',
    },
    warning: {
      solid: '#d28a20',
      softBg: 'rgba(210, 138, 32, 0.14)',
      softFg: '#b57412',
      border: 'rgba(210, 138, 32, 0.42)',
    },
    neutral: {
      solid: '#647067',
      softBg: 'rgba(100, 112, 103, 0.12)',
      softFg: '#647067',
      border: 'rgba(100, 112, 103, 0.35)',
    },
  }[tone];

  return (
    <Chip
      size="small"
      label={label}
      sx={{
        bgcolor: appearance === 'solid' ? palette.solid : palette.softBg,
        color: appearance === 'solid' ? '#ffffff' : palette.softFg,
        border: '1px solid',
        borderColor: appearance === 'solid' ? palette.solid : palette.border,
      }}
    />
  );
}

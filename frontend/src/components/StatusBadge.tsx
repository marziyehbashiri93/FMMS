import { Box, Chip } from '@mui/material';
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

function StatusDot({ color }: { color: string }) {
  return (
    <Box
      component="span"
      sx={{
        width: 7,
        height: 7,
        borderRadius: '50%',
        bgcolor: color,
        boxShadow: `0 0 0 3px ${color}33`,
        flexShrink: 0,
        display: 'inline-block',
      }}
    />
  );
}

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
  const isSolid = appearance === 'solid';
  return (
    <Chip
      size="small"
      icon={<StatusDot color={isSolid ? '#ffffff' : config.bg} />}
      label={label || config.label}
      sx={{
        minWidth: 76,
        height: 28,
        fontWeight: 800,
        bgcolor: isSolid ? config.bg : config.softBg,
        color: isSolid ? '#ffffff' : config.bg,
        border: '1px solid',
        borderColor: isSolid ? config.bg : config.border,
        boxShadow: isSolid ? `0 4px 10px ${config.bg}44` : 'none',
        '& .MuiChip-icon': { ml: 0.75, mr: -0.25 },
        '& .MuiChip-label': { px: 1, fontWeight: 800 },
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

  const isSolid = appearance === 'solid';
  const dotColor = isSolid ? '#ffffff' : palette.softFg;

  return (
    <Chip
      size="small"
      icon={<StatusDot color={dotColor} />}
      label={label}
      sx={{
        height: 28,
        fontWeight: 800,
        bgcolor: isSolid ? palette.solid : palette.softBg,
        color: isSolid ? '#ffffff' : palette.softFg,
        border: '1px solid',
        borderColor: isSolid ? palette.solid : palette.border,
        boxShadow: isSolid ? `0 4px 10px ${palette.solid}40` : 'none',
        '& .MuiChip-icon': { ml: 0.75, mr: -0.25 },
        '& .MuiChip-label': { px: 1, fontWeight: 800 },
      }}
    />
  );
}

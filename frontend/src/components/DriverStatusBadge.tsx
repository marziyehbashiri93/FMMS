import { Box, Chip } from '@mui/material';
import type { DriverStatus } from '../types/fmms';

const styles: Record<DriverStatus, { bg: string; softBg: string; border: string; label: string }> = {
  ACTIVE: {
    bg: '#248a57',
    softBg: 'rgba(36, 138, 87, 0.12)',
    border: 'rgba(36, 138, 87, 0.35)',
    label: 'فعال',
  },
  DECOMMISSIONED: {
    bg: '#9f2f27',
    softBg: 'rgba(159, 47, 39, 0.12)',
    border: 'rgba(159, 47, 39, 0.36)',
    label: 'غیرفعال',
  },
};

export function DriverStatusBadge({
  status,
  label,
}: {
  status: string;
  label?: string;
}) {
  const config = styles[status as DriverStatus] ?? {
    bg: '#647067',
    softBg: 'rgba(100, 112, 103, 0.12)',
    border: 'rgba(100, 112, 103, 0.35)',
    label: status,
  };
  return (
    <Chip
      size="small"
      icon={
        <Box
          component="span"
          sx={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            bgcolor: config.bg,
            boxShadow: `0 0 0 3px ${config.bg}33`,
            display: 'inline-block',
          }}
        />
      }
      label={label || config.label}
      sx={{
        minWidth: 76,
        height: 28,
        fontWeight: 800,
        bgcolor: config.softBg,
        color: config.bg,
        border: '1px solid',
        borderColor: config.border,
        '& .MuiChip-icon': { ml: 0.75, mr: -0.25 },
        '& .MuiChip-label': { px: 1, fontWeight: 800 },
      }}
    />
  );
}

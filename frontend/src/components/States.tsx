import { Alert, Box, CircularProgress, Typography } from '@mui/material';
import { Inbox, Refresh } from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';
import { Button } from './Button';

export function LoadingState({ label = 'در حال دریافت اطلاعات' }: { label?: string }) {
  return (
    <Box display="flex" alignItems="center" justifyContent="center" gap={1.5} py={6}>
      <CircularProgress size={22} />
      <Typography color="text.secondary">{label}</Typography>
    </Box>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <Alert
      severity="error"
      action={
        <Button
          variant="outlined"
          color="error"
          size="small"
          startIcon={<Refresh />}
          onClick={onRetry}
          sx={{
            minWidth: 'auto',
            px: 1.5,
            bgcolor: 'common.white',
            borderColor: 'error.main',
            color: 'error.dark',
            fontWeight: 800,
            '&:hover': {
              bgcolor: 'rgba(239, 68, 68, 0.08)',
              borderColor: 'error.dark',
            },
          }}
        >
          تلاش مجدد
        </Button>
      }
    >
      {message}
    </Alert>
  );
}

export function EmptyState({
  title,
  subtitle,
  icon: Icon = Inbox,
}: {
  title: string;
  subtitle?: string;
  icon?: SvgIconComponent;
}) {
  return (
    <Box py={6} textAlign="center">
      <Box
        sx={{
          width: 52,
          height: 52,
          borderRadius: (t) => t.radius('xl'),
          bgcolor: 'secondary.light',
          color: 'secondary.dark',
          display: 'grid',
          placeItems: 'center',
          mx: 'auto',
          mb: 1.5,
        }}
      >
        <Icon />
      </Box>
      <Typography fontWeight={800}>{title}</Typography>
      {subtitle && (
        <Typography color="text.secondary" mt={0.75}>
          {subtitle}
        </Typography>
      )}
    </Box>
  );
}

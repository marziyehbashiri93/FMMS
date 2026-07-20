import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import { Inbox, Refresh } from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';

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
        <Button color="inherit" size="small" startIcon={<Refresh />} onClick={onRetry}>
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
          borderRadius: 2,
          bgcolor: 'primary.light',
          color: 'primary.main',
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

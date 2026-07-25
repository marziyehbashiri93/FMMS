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

function EmptyVisual({
  title,
  subtitle,
  Icon,
  showDefaultHint = false,
}: {
  title: string;
  subtitle?: string;
  Icon: SvgIconComponent;
  showDefaultHint?: boolean;
}) {
  const hint = subtitle || (showDefaultHint ? 'به‌محض ثبت اطلاعات، اینجا نمایش داده می‌شود.' : undefined);

  return (
    <Box textAlign="center" px={1}>
      <Box
        sx={{
          width: 88,
          height: 88,
          mx: 'auto',
          mb: 2.25,
          borderRadius: '50%',
          display: 'grid',
          placeItems: 'center',
          position: 'relative',
          background: (theme) =>
            `radial-gradient(circle at 35% 30%, ${theme.palette.primary.light} 0%, rgba(15,107,76,0.10) 55%, rgba(196,92,74,0.10) 100%)`,
          boxShadow: 'inset 0 0 0 1px rgba(15, 107, 76, 0.10)',
          '&::after': {
            content: '""',
            position: 'absolute',
            inset: -8,
            borderRadius: '50%',
            border: '1px dashed',
            borderColor: 'rgba(15, 107, 76, 0.18)',
            pointerEvents: 'none',
          },
        }}
      >
        <Icon sx={{ fontSize: 36, color: 'primary.main', opacity: 0.92 }} />
      </Box>
      <Typography
        sx={{
          fontWeight: 800,
          fontSize: '1.05rem',
          color: 'text.primary',
          lineHeight: 1.5,
        }}
      >
        {title}
      </Typography>
      {hint && (
        <Typography
          sx={{
            mt: 0.85,
            color: subtitle ? 'text.secondary' : 'text.disabled',
            fontSize: '0.875rem',
            lineHeight: 1.7,
            maxWidth: 320,
            mx: 'auto',
          }}
        >
          {hint}
        </Typography>
      )}
    </Box>
  );
}

export function EmptyState({
  title,
  subtitle,
  icon: Icon = Inbox,
  boxed = true,
}: {
  title: string;
  subtitle?: string;
  icon?: SvgIconComponent;
  /** Soft panel for modal/page empty areas; false keeps table-inline empty. */
  boxed?: boolean;
}) {
  if (!boxed) {
    return (
      <Box py={5} textAlign="center">
        <EmptyVisual title={title} subtitle={subtitle} Icon={Icon} />
      </Box>
    );
  }

  const visual = (
    <EmptyVisual title={title} subtitle={subtitle} Icon={Icon} showDefaultHint />
  );

  return (
    <Box
      sx={{
        width: '100%',
        height: '100%',
        minHeight: 280,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        py: { xs: 2, sm: 3 },
        px: { xs: 1, sm: 2 },
      }}
    >
      <Box
        sx={{
          width: '100%',
          maxWidth: 480,
          textAlign: 'center',
          px: { xs: 3, sm: 4.5 },
          py: { xs: 4, sm: 5 },
          borderRadius: (t) => t.radius('lg'),
          border: '1px dashed',
          borderColor: 'rgba(15, 107, 76, 0.22)',
          bgcolor: 'rgba(255,255,255,0.72)',
          backgroundImage: (theme) =>
            `linear-gradient(165deg, ${theme.palette.common.white} 0%, ${theme.palette.primary.light}55 48%, ${theme.palette.secondary.light}66 100%)`,
          boxShadow: '0 10px 28px rgba(15, 107, 76, 0.06)',
        }}
      >
        {visual}
      </Box>
    </Box>
  );
}

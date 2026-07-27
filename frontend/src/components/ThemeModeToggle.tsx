import { IconButton, Tooltip } from '@mui/material';
import { DarkModeRounded, LightModeRounded } from '@mui/icons-material';
import { useColorMode } from '../theme/theme';

/**
 * Toggle between light and dark color modes (persisted in localStorage).
 */
export function ThemeModeToggle({ size = 'medium' }: { size?: 'small' | 'medium' }) {
  const { mode, toggleColorMode } = useColorMode();
  const isDark = mode === 'dark';

  return (
    <Tooltip title={isDark ? 'حالت روشن' : 'حالت تاریک'} arrow>
      <IconButton
        onClick={toggleColorMode}
        aria-label={isDark ? 'فعال‌سازی حالت روشن' : 'فعال‌سازی حالت تاریک'}
        size={size}
        sx={{
          color: 'text.secondary',
          border: '1px solid',
          borderColor: 'divider',
          bgcolor: (t) =>
            t.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(15,107,76,0.04)',
          width: size === 'small' ? 36 : 40,
          height: size === 'small' ? 36 : 40,
          transition: 'all .2s ease',
          '&:hover': {
            color: 'primary.main',
            borderColor: 'primary.main',
            bgcolor: 'action.hover',
            transform: 'rotate(-12deg)',
          },
        }}
      >
        {isDark ? <LightModeRounded fontSize="small" /> : <DarkModeRounded fontSize="small" />}
      </IconButton>
    </Tooltip>
  );
}

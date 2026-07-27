import { Box } from '@mui/material';
import type { Theme } from '@mui/material/styles';
import type { ReactNode } from 'react';

export type IconWellTone = 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';

type IconWellProps = {
  tone?: IconWellTone;
  size?: number;
  children: ReactNode;
};

/**
 * Square icon plate with soft colored rim + mild glow.
 * Glow strength is identical in light and dark modes.
 */
export function iconWellSx(tone: IconWellTone, theme: Theme, size = 46) {
  const c = theme.palette[tone];
  const isDark = theme.palette.mode === 'dark';
  const radius = Math.round(size * 0.26);
  const innerRadius = Math.max(radius - 2, 6);

  return {
    width: size,
    height: size,
    borderRadius: `${radius}px`,
    display: 'grid',
    placeItems: 'center',
    flexShrink: 0,
    position: 'relative' as const,
    background: isDark
      ? `linear-gradient(160deg, ${c.main}1A 0%, rgba(0,0,0,0.28) 100%)`
      : `linear-gradient(160deg, ${c.main}12 0%, ${c.main}08 100%)`,
    border: '1.5px solid',
    borderColor: isDark ? `${c.main}55` : `${c.main}48`,
    // Mild, equal glow in both modes
    boxShadow: [
      `0 0 0 1px ${c.main}10`,
      `0 0 10px ${c.main}22`,
      isDark ? '0 4px 10px rgba(0,0,0,0.28)' : `0 3px 8px ${c.main}14`,
      isDark
        ? 'inset 0 1px 0 rgba(255,255,255,0.07)'
        : 'inset 0 1px 0 rgba(255,255,255,0.85)',
    ].join(', '),
    '&::before': {
      content: '""',
      position: 'absolute',
      inset: 2,
      borderRadius: `${innerRadius}px`,
      background: isDark
        ? 'linear-gradient(180deg, rgba(255,255,255,0.10) 0%, transparent 42%)'
        : 'linear-gradient(180deg, rgba(255,255,255,0.7) 0%, transparent 48%)',
      pointerEvents: 'none',
    },
    '& svg': {
      position: 'relative',
      zIndex: 1,
      fontSize: size * 0.45,
      color: isDark ? c.main : c.dark,
      // Soft, equal icon glow
      filter: `drop-shadow(0 0 3px ${c.main}40)`,
    },
  };
}

export function IconWell({ tone = 'primary', size = 46, children }: IconWellProps) {
  return <Box sx={(theme) => iconWellSx(tone, theme, size)}>{children}</Box>;
}

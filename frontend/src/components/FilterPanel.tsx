import { Card, CardContent, Stack } from '@mui/material';
import type { ReactNode } from 'react';

export function FilterPanel({ children }: { children: ReactNode }) {
  return (
    <Card
      sx={{
        bgcolor: (t) =>
          t.palette.mode === 'dark' ? 'rgba(21, 28, 24, 0.9)' : 'rgba(255,255,255,0.88)',
        border: '1px solid',
        borderColor: 'divider',
        boxShadow: (t) =>
          t.palette.mode === 'dark'
            ? '0 8px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)'
            : '0 8px 24px rgba(15, 107, 76, 0.06), inset 0 1px 0 rgba(255,255,255,0.9)',
        backdropFilter: 'blur(8px)',
        overflow: 'visible',
      }}
    >
      <CardContent sx={{ p: { xs: 1.5, md: 2 }, '&:last-child': { pb: { xs: 1.5, md: 2 } } }}>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          useFlexGap
          alignItems={{ xs: 'stretch', md: 'center' }}
          sx={{
            direction: 'rtl',
            gap: { xs: 1.5, md: 2 },
            '& > *': { margin: 0 },
          }}
        >
          {children}
        </Stack>
      </CardContent>
    </Card>
  );
}

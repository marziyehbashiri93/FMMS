import { Card, CardContent, Stack } from '@mui/material';
import type { ReactNode } from 'react';

export function FilterPanel({ children }: { children: ReactNode }) {
  return (
    <Card>
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

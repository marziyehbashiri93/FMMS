import { Box, Stack } from '@mui/material';
import type { ReactNode } from 'react';

type FeaturePageProps = {
  children: ReactNode;
};

type KpiGridProps = {
  children: ReactNode;
  mdColumns?: number;
  xlColumns?: number;
};

export function FeaturePage({ children }: FeaturePageProps) {
  return (
    <Stack
      spacing={{ xs: 1.5, md: 2.25 }}
      sx={{
        direction: 'rtl',
        textAlign: 'right',
      }}
    >
      {children}
    </Stack>
  );
}

export function KpiGrid({ children, mdColumns = 3, xlColumns }: KpiGridProps) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: {
          xs: 'repeat(2, minmax(0, 1fr))',
          md: `repeat(${mdColumns}, minmax(0, 1fr))`,
          ...(xlColumns ? { xl: `repeat(${xlColumns}, minmax(0, 1fr))` } : {}),
        },
        gap: 1.5,
      }}
    >
      {children}
    </Box>
  );
}

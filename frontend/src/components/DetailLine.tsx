import { Box, Typography } from '@mui/material';
import type { ReactNode } from 'react';

export function DetailLine({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'minmax(110px, 36%) 1fr',
        gap: 1.5,
        alignItems: 'center',
        py: 1.25,
        borderBottom: '1px solid',
        borderColor: 'divider',
        '&:last-child': { borderBottom: 'none' },
      }}
    >
      <Typography variant="body2" color="text.secondary" fontWeight={600}>
        {label}
      </Typography>
      <Box textAlign="left" minWidth={0} sx={{ justifySelf: 'start' }}>
        {value}
      </Box>
    </Box>
  );
}

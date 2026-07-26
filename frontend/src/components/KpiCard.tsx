import { Box, Card, CardContent, Typography } from '@mui/material';
import type { SvgIconComponent } from '@mui/icons-material';

export function KpiCard({
  label,
  value,
  helper,
  icon: Icon,
  tone = 'primary',
}: {
  label: string;
  value: string | number;
  helper?: string;
  icon: SvgIconComponent;
  tone?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info';
}) {
  return (
    <Card>
      <CardContent sx={{ p: { xs: 1.5, md: 1.75 }, '&:last-child': { pb: { xs: 1.5, md: 1.75 } } }}>
        <Box display="flex" alignItems="center" justifyContent="space-between" gap={1.5} style={{ direction: 'rtl' }}>
          <Box minWidth={0} style={{ textAlign: 'right', direction: 'rtl' }}>
            <Typography variant="caption" color="text.primary" display="block" mb={0.75} fontWeight={900}>
              {label}
            </Typography>
            <Typography variant="h2" color="text.primary" noWrap>
              {value}
            </Typography>
            {helper && (
              <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                {helper}
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              width: 44,
              height: 44,
              borderRadius: (t) => t.radius('lg'),
              bgcolor: `${tone}.light`,
              color: `${tone}.dark`,
              display: 'grid',
              placeItems: 'center',
              flexShrink: 0,
            }}
          >
            <Icon fontSize="medium" />
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

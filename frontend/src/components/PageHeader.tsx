import { Breadcrumbs, Card, CardContent, Link, Stack, Typography } from '@mui/material';
import { ArrowLeft } from '@mui/icons-material';
import type { ReactNode } from 'react';
import { Link as RouterLink } from 'react-router-dom';

export interface Crumb {
  label: string;
  to?: string;
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
}: {
  title: string;
  description?: string;
  breadcrumbs: Crumb[];
  actions?: ReactNode;
}) {
  return (
    <Card
      sx={{
        borderColor: 'divider',
        boxShadow: '0 8px 22px rgba(21, 95, 61, 0.06)',
      }}
    >
      <CardContent sx={{ p: { xs: 1.75, md: 2.25 }, '&:last-child': { pb: { xs: 1.75, md: 2.25 } } }}>
        <Stack spacing={1.5}>
          <Breadcrumbs
            separator={<ArrowLeft sx={{ fontSize: 18, color: 'text.secondary' }} />}
            sx={{ '& .MuiBreadcrumbs-ol': { justifyContent: 'flex-start' } }}
          >
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;
              if (crumb.to && !isLast) {
                return (
                  <Link key={crumb.label} component={RouterLink} to={crumb.to} underline="hover" color="text.secondary">
                    {crumb.label}
                  </Link>
                );
              }
              return (
                <Typography key={crumb.label} color={isLast ? 'text.primary' : 'text.secondary'} fontWeight={isLast ? 800 : 500}>
                  {crumb.label}
                </Typography>
              );
            })}
          </Breadcrumbs>

          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} gap={1.5}>
            <Stack spacing={0.5} minWidth={0}>
              <Typography variant="h1">{title}</Typography>
              {description && (
                <Typography color="text.secondary">
                  {description}
                </Typography>
              )}
            </Stack>
            {actions && (
              <Stack direction="row" gap={1} flexWrap="wrap" justifyContent={{ xs: 'flex-start', md: 'flex-end' }}>
                {actions}
              </Stack>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

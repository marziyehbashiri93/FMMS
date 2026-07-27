import { Box, Breadcrumbs, Card, CardContent, Link, Stack, Typography } from '@mui/material';
import type { ReactNode } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { brandAccentBarGradient } from '../theme/gradients';

export interface Crumb {
  label: string;
  to?: string;
}

/** Soft rounded triangle pointing left (RTL breadcrumb separator). */
function BreadcrumbSeparator() {
  return (
    <Box
      component="svg"
      viewBox="0 0 14 16"
      aria-hidden
      sx={{
        width: 9,
        height: 10,
        color: 'text.secondary',
        mx: 0.35,
        flexShrink: 0,
        display: 'block',
      }}
    >
      <path
        fill="currentColor"
        stroke="currentColor"
        strokeWidth={2.4}
        strokeLinejoin="round"
        strokeLinecap="round"
        d="M10.5 3.2 3.6 8l6.9 4.8z"
      />
    </Box>
  );
}

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  accentColor,
  accentSide = 'start',
  backgroundImage,
  backgroundSize = '420px auto',
  backgroundPosition = 'left 24px center',
}: {
  title: string;
  description?: string;
  breadcrumbs: Crumb[];
  actions?: ReactNode;
  accentColor?: string;
  accentSide?: 'start' | 'right';
  backgroundImage?: string;
  backgroundSize?: string;
  backgroundPosition?: string;
}) {
  return (
    <Card
      sx={{
        bgcolor: (t) =>
          t.palette.mode === 'dark' ? 'rgba(21, 28, 24, 0.94)' : 'rgba(255,255,255,0.94)',
        backgroundImage: backgroundImage ? `url("${backgroundImage}")` : undefined,
        backgroundPosition,
        backgroundRepeat: 'no-repeat',
        backgroundSize,
        border: '1px solid',
        borderColor: 'divider',
        boxShadow: (t) =>
          t.palette.mode === 'dark'
            ? '0 12px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)'
            : '0 12px 32px rgba(15, 107, 76, 0.08), inset 0 1px 0 rgba(255,255,255,0.9)',
        position: 'relative',
        overflow: 'hidden',
        backdropFilter: 'blur(6px)',
        '&::before': {
          content: '""',
          position: 'absolute',
          ...(accentSide === 'right' ? { right: 0 } : { insetInlineStart: 0 }),
          top: 0,
          bottom: 0,
          width: 4,
          ...(accentColor
            ? { bgcolor: accentColor }
            : {
                background: (theme) =>
                  brandAccentBarGradient(theme.palette.primary, theme.palette.secondary),
              }),
          zIndex: 1,
        },
      }}
    >
      <CardContent
        sx={{
          p: { xs: 1.75, md: 2.25 },
          '&:last-child': { pb: { xs: 1.75, md: 2.25 } },
          position: 'relative',
          zIndex: 2,
        }}
      >
        <Stack spacing={1.25}>
          <Breadcrumbs
            separator={<BreadcrumbSeparator />}
            sx={{
              '& .MuiBreadcrumbs-ol': { justifyContent: 'flex-start', alignItems: 'center' },
              '& .MuiBreadcrumbs-separator': { mx: 0.75 },
            }}
          >
            {breadcrumbs.map((crumb, index) => {
              const isLast = index === breadcrumbs.length - 1;
              if (crumb.to && !isLast) {
                return (
                  <Link
                    key={crumb.label}
                    component={RouterLink}
                    to={crumb.to}
                    underline="hover"
                    color="text.secondary"
                  >
                    {crumb.label}
                  </Link>
                );
              }
              return (
                <Typography
                  key={crumb.label}
                  color={isLast ? 'text.primary' : 'text.secondary'}
                  fontWeight={isLast ? 800 : 500}
                >
                  {crumb.label}
                </Typography>
              );
            })}
          </Breadcrumbs>

          <Stack
            direction={{ xs: 'column', md: 'row' }}
            justifyContent="space-between"
            alignItems={{ md: 'center' }}
            gap={1.5}
          >
            <Stack spacing={0.5} minWidth={0}>
              <Typography variant="h1">{title}</Typography>
              {description && (
                <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 640 }}>
                  {description}
                </Typography>
              )}
            </Stack>
            {actions && (
              <Stack
                direction="row"
                gap={1}
                flexWrap="wrap"
                justifyContent={{ xs: 'flex-start', md: 'flex-end' }}
              >
                {actions}
              </Stack>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

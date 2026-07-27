import { Box, Tab, Tabs, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import type { ReactElement, ReactNode, SyntheticEvent } from 'react';

export type AppTabItem<T extends string | number = string> = {
  value: T;
  label: ReactNode;
  icon?: ReactElement;
  disabled?: boolean;
};

type AppTabsProps<T extends string | number = string> = {
  value: T;
  onChange: (value: T) => void;
  items: ReadonlyArray<AppTabItem<T>>;
  ariaLabel?: string;
  scrollable?: boolean;
  size?: 'sm' | 'md';
  sx?: object;
};

/**
 * Flat tabs, no outer container/box — the selected tab is marked by a
 * short secondary-colored underline beneath its label (classic tab
 * indicator), everything else stays transparent.
 */
export function AppTabs<T extends string | number = string>({
  value,
  onChange,
  items,
  ariaLabel = 'تب‌ها',
  scrollable,
  size = 'md',
  sx,
}: AppTabsProps<T>) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const dense = size === 'sm';
  const forceScroll = scrollable ?? isMobile;

  const handleChange = (_event: SyntheticEvent, next: T) => {
    onChange(next);
  };

  return (
    <Box sx={{ ...((sx as object) ?? {}) }}>
      <Tabs
        value={value}
        onChange={handleChange}
        variant={forceScroll ? 'scrollable' : 'standard'}
        scrollButtons={forceScroll ? 'auto' : false}
        allowScrollButtonsMobile
        aria-label={ariaLabel}
        TabIndicatorProps={{
          sx: {
            height: 2.5,
            borderRadius: '2px',
            backgroundColor: 'secondary.main',
          },
        }}
        sx={{
          minHeight: dense ? 36 : 40,
          '& .MuiTabs-flexContainer': {
            gap: 1.5,
            ...(forceScroll ? {} : { justifyContent: 'flex-start' }),
          },
          '& .MuiTabs-scroller': {
            overflow: 'auto !important',
          },
          '& .MuiTabs-scrollButtons': {
            color: 'text.secondary',
            '&.Mui-disabled': { opacity: 0.25 },
          },
        }}
      >
        {items.map((item) => (
          <Tab
            key={String(item.value)}
            value={item.value}
            label={item.label}
            icon={item.icon}
            iconPosition={item.icon ? 'start' : undefined}
            disabled={item.disabled}
            disableRipple
            sx={{
              minHeight: dense ? 34 : 38,
              minWidth: 'auto',
              px: { xs: 0.5, md: dense ? 0.5 : 0.75 },
              py: dense ? 0.5 : 0.65,
              gap: 0.75,
              textTransform: 'none',
              fontWeight: 700,
              fontSize: { xs: '0.8rem', md: dense ? '0.82rem' : '0.875rem' },
              color: 'text.secondary',
              bgcolor: 'transparent',
              transition: 'all .18s ease',
              '& .MuiTab-iconWrapper': {
                marginBottom: '0 !important',
                marginLeft: 0,
                marginRight: 0,
                '& svg': { fontSize: dense ? '1.05rem' : '1.15rem' },
              },
              '&:hover': {
                color: 'text.primary',
              },
              '&.Mui-selected': {
                color: 'text.primary',
                fontWeight: 800,
                bgcolor: 'transparent',
              },
              '&.Mui-disabled': {
                opacity: 0.45,
              },
            }}
          />
        ))}
      </Tabs>
    </Box>
  );
}

import { Box, Tab, Tabs, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';

export type StatusTabOption<T extends string = string> = {
  value: T | '';
  label: string;
};

type StatusFilterTabsProps<T extends string> = {
  value: T | '';
  options: ReadonlyArray<StatusTabOption<T>>;
  onChange: (value: T | '') => void;
  ariaLabel?: string;
};

/**
 * Scrollable status tabs: first option is typically «همه», then one tab per status.
 */
export function StatusFilterTabs<T extends string>({
  value,
  options,
  onChange,
  ariaLabel = 'فیلتر وضعیت',
}: StatusFilterTabsProps<T>) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  return (
    <Box
      sx={{
        pt: 0.5,
        px: 0.5,
        pb: 0,
        borderRadius: (t) => t.radius('md'),
        bgcolor: 'action.disabledBackground',
        border: '1px solid',
        borderColor: 'divider',
        overflow: 'hidden',
      }}
    >
      <Tabs
        value={value}
        onChange={(_, next: T | '') => onChange(next)}
        variant="scrollable"
        scrollButtons={isMobile ? 'auto' : false}
        allowScrollButtonsMobile
        aria-label={ariaLabel}
        TabIndicatorProps={{
          sx: {
            height: 3,
            borderRadius: '3px 3px 0 0',
            bgcolor: 'secondary.main',
            bottom: 0,
          },
        }}
        sx={{
          minHeight: 44,
          '& .MuiTabs-flexContainer': {
            gap: 0.5,
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
        {options.map((option) => (
          <Tab
            key={option.value || 'all'}
            value={option.value}
            label={option.label}
            disableRipple
            sx={{
              minHeight: 44,
              minWidth: 'auto',
              px: { xs: 1.5, md: 2.25 },
              py: 0.75,
              pb: 1.25,
              borderRadius: (t) => t.radius('sm'),
              textTransform: 'none',
              fontWeight: 700,
              fontSize: { xs: '0.82rem', md: '0.875rem' },
              color: 'text.secondary',
              bgcolor: 'transparent',
              transition: 'color .15s ease',
              '&:hover': {
                color: 'text.primary',
                bgcolor: 'transparent',
              },
              '&.Mui-selected': {
                color: 'primary.dark',
                bgcolor: 'transparent',
              },
            }}
          />
        ))}
      </Tabs>
    </Box>
  );
}

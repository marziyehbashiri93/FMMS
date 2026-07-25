import { useEffect, useState, type ReactNode, type SyntheticEvent } from 'react';
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Tab,
  Tabs,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { Close } from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';
import { EmptyState, ErrorState, LoadingState } from './States';

export type TabbedDetailModalTab = {
  label: string;
  content: ReactNode;
};

export type TabbedDetailModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  icon?: SvgIconComponent;
  tabs: TabbedDetailModalTab[];
  loading?: boolean;
  loadingLabel?: string;
  error?: string;
  onRetry?: () => void;
  emptyTitle?: string;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  activeTab?: number;
  onTabChange?: (index: number) => void;
};

function TabPanel({
  value,
  index,
  children,
}: {
  value: number;
  index: number;
  children: ReactNode;
}) {
  if (value !== index) return null;
  return <Box sx={{ pt: 2.25 }}>{children}</Box>;
}

/**
 * Shared detail modal with RTL header and scrollable tabs.
 * Use across feature pages to keep modal design consistent.
 */
export function TabbedDetailModal({
  open,
  onClose,
  title,
  icon: Icon,
  tabs,
  loading = false,
  loadingLabel = 'در حال دریافت اطلاعات',
  error = '',
  onRetry,
  emptyTitle = 'موردی برای نمایش وجود ندارد',
  maxWidth = 'md',
  activeTab,
  onTabChange,
}: TabbedDetailModalProps) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const [internalTab, setInternalTab] = useState(0);
  const tab = activeTab ?? internalTab;

  useEffect(() => {
    if (open) {
      if (onTabChange) onTabChange(0);
      else setInternalTab(0);
    }
  }, [open]);

  const handleTabChange = (_event: SyntheticEvent, nextTab: number) => {
    if (onTabChange) onTabChange(nextTab);
    else setInternalTab(nextTab);
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullScreen={fullScreen}
      maxWidth={maxWidth}
      fullWidth
      scroll="paper"
      disableScrollLock
      dir="rtl"
      PaperProps={{
        sx: {
          borderRadius: fullScreen ? 0 : theme.radius('md'),
          minHeight: { sm: 560 },
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(23, 35, 29, 0.18)',
        },
      }}
    >
      <DialogTitle
        sx={{
          py: 2,
          px: { xs: 2, sm: 2.5 },
          bgcolor: 'rgba(0, 167, 111, 0.04)',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={2}>
          <Stack direction="row" alignItems="center" gap={1.5} minWidth={0}>
            {Icon && (
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: (t) => t.radius('xl'),
                  display: 'grid',
                  placeItems: 'center',
                  background: (theme) =>
                    `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.secondary.main} 100%)`,
                  color: 'common.white',
                  flexShrink: 0,
                }}
              >
                <Icon fontSize="small" />
              </Box>
            )}
            <Typography variant="h2" noWrap>
              {title}
            </Typography>
          </Stack>
          <IconButton
            size="small"
            onClick={onClose}
            aria-label="بستن"
            sx={{
              width: 28,
              height: 28,
              color: 'text.secondary',
              '&:hover': {
                color: 'text.primary',
                bgcolor: 'rgba(20, 26, 33, 0.06)',
              },
            }}
          >
            <Close sx={{ fontSize: 18 }} />
          </IconButton>
        </Stack>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 1.5, sm: 2.5 }, pt: { xs: 2.5, sm: 3 }, pb: 2 }}>
        {loading && <LoadingState label={loadingLabel} />}
        {!loading && error && onRetry && <ErrorState message={error} onRetry={onRetry} />}
        {!loading && !error && tabs.length === 0 && <EmptyState title={emptyTitle} />}
        {!loading && !error && tabs.length > 0 && (
          <>
            <Tabs
              value={Math.min(tab, tabs.length - 1)}
              onChange={handleTabChange}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              sx={{
                mt: 0.5,
                minHeight: 44,
                bgcolor: 'rgba(244, 246, 248, 0.9)',
                borderRadius: (t) => t.radius('md'),
                px: 0.5,
                '& .MuiTabs-indicator': {
                  height: 3,
                  borderRadius: (t) => t.radius('md'),
                  bgcolor: 'secondary.main',
                },
                '& .MuiTab-root': {
                  minHeight: 44,
                  fontWeight: 700,
                  textTransform: 'none',
                  color: 'text.secondary',
                  '&.Mui-selected': { color: 'primary.dark' },
                },
              }}
            >
              {tabs.map((item) => (
                <Tab key={item.label} label={item.label} />
              ))}
            </Tabs>

            {tabs.map((item, index) => (
              <TabPanel key={item.label} value={Math.min(tab, tabs.length - 1)} index={index}>
                {item.content}
              </TabPanel>
            ))}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

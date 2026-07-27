import { useEffect, useState, type ReactNode } from 'react';
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { Close } from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';
import { AppTabs } from './AppTabs';
import { IconWell } from './IconWell';
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

const MODAL_HEIGHT = { xs: '100%', sm: 640, md: 680 };

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
  return (
    <Box
      sx={{
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {children}
    </Box>
  );
}

/**
 * Shared detail modal with RTL header, fixed height, and scrollable body.
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
      slotProps={{
        backdrop: {
          sx: {
            backgroundColor: 'rgba(23, 35, 29, 0.42)',
            backdropFilter: 'blur(8px)',
            WebkitBackdropFilter: 'blur(8px)',
          },
        },
      }}
      PaperProps={{
        sx: {
          borderRadius: fullScreen ? 0 : theme.radius('md'),
          height: fullScreen ? '100%' : MODAL_HEIGHT,
          maxHeight: fullScreen ? '100%' : MODAL_HEIGHT,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(23, 35, 29, 0.18)',
        },
      }}
    >
      <DialogTitle
        sx={{
          flexShrink: 0,
          pt: 2,
          pb: 2.25,
          px: { xs: 2, sm: 2.5 },
          bgcolor: 'rgba(15, 107, 76, 0.04)',
          borderBottom: '1px solid',
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={2}>
          <Stack direction="row" alignItems="center" gap={1.5} minWidth={0}>
            {Icon && (
              <IconWell tone="secondary" size={40}>
                <Icon />
              </IconWell>
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

      <DialogContent
        sx={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          px: { xs: 1.5, sm: 2.5 },
          pb: 2,
          overflow: 'hidden',
          // MUI sets padding-top: 0 when content follows DialogTitle — force gap under title.
          pt: { xs: '28px !important', sm: '15px !important' },
        }}
      >
        {loading && (
          <Box flex={1} display="flex" alignItems="center" justifyContent="center" minHeight={0}>
            <LoadingState label={loadingLabel} />
          </Box>
        )}
        {!loading && error && onRetry && (
          <Box flex={1} display="flex" alignItems="center" justifyContent="center" minHeight={0}>
            <ErrorState message={error} onRetry={onRetry} />
          </Box>
        )}
        {!loading && !error && tabs.length === 0 && (
          <Box flex={1} display="flex" alignItems="center" justifyContent="center" minHeight={0}>
            <EmptyState title={emptyTitle} boxed />
          </Box>
        )}
        {!loading && !error && tabs.length > 0 && (
          <>
            <AppTabs
              value={Math.min(tab, tabs.length - 1)}
              onChange={(next) => {
                setInternalTab(next);
                onTabChange?.(next);
              }}
              ariaLabel="بخش‌های جزئیات"
              scrollable
              items={tabs.map((item, index) => ({
                value: index,
                label: item.label,
              }))}
            />

            <Box
              sx={{
                flex: 1,
                minHeight: 0,
                mt: 2.5,
                overflow: 'auto',
              }}
            >
              {tabs.map((item, index) => (
                <TabPanel key={item.label} value={Math.min(tab, tabs.length - 1)} index={index}>
                  {item.content}
                </TabPanel>
              ))}
            </Box>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

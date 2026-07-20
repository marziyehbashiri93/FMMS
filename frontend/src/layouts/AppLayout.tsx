import { useMemo, useState } from 'react';
import {
  AppBar,
  Box,
  BottomNavigation,
  BottomNavigationAction,
  Button,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material';
import { ChevronLeft, ChevronRight, Logout, Menu } from '@mui/icons-material';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';
import { modules, type AppModule } from '../app/modules';
import { api } from '../api/client';

const drawerWidth = 244;
const collapsedDrawerWidth = 88;
const sidebarBg = '#141A21';
const sidebarText = '#919EAB';
const sidebarMuted = '#637381';
const sidebarActive = '#5BE49B';
const sidebarActiveBg = 'rgba(0, 167, 111, 0.08)';

function BrandBlock({ compact = false, onDark = false }: { compact?: boolean; onDark?: boolean }) {
  return (
    <Stack
      direction="row"
      alignItems="center"
      justifyContent={compact ? 'center' : 'flex-start'}
      spacing={1}
      style={{ direction: 'rtl', textAlign: 'right' }}
    >
      <Box
        sx={{
          width: compact ? 34 : 36,
          height: compact ? 34 : 36,
          borderRadius: 1.5,
          bgcolor: compact && onDark ? 'transparent' : 'primary.main',
          color: 'primary.contrastText',
          display: 'grid',
          placeItems: 'center',
          fontWeight: 900,
          boxShadow: '0 10px 24px rgba(31,111,74,0.22)',
          flexShrink: 0,
          border: compact && onDark ? '1px solid rgba(91, 228, 155, 0.36)' : 'none',
        }}
      >
        گ
      </Box>
      {!compact && (
        <Box minWidth={0} flex={1}>
          <Typography fontWeight={900} lineHeight={1.2} noWrap fontSize="0.86rem" color={onDark ? '#ffffff' : 'text.primary'}>
            مدیریت نگهداری ناوگان
          </Typography>
          <Typography variant="caption" color={onDark ? sidebarText : 'text.secondary'} noWrap>
            گروه صنعتی گلستان
          </Typography>
        </Box>
      )}
    </Stack>
  );
}

const menuSections: Array<{ label: string; items: AppModule[] }> = [
  {
    label: 'اصلی',
    items: modules.filter((item) => ['dashboard', 'vehicles', 'components', 'drivers', 'inspections', 'faults'].includes(item.key)),
  },
  {
    label: 'مدیریت',
    items: modules.filter((item) => !['dashboard', 'vehicles', 'components', 'drivers', 'inspections', 'faults'].includes(item.key)),
  },
];

function NavigationList({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <List disablePadding sx={{ px: collapsed ? 1 : 1.5, py: 1.5 }}>
      {menuSections.map((section) => (
        <Box key={section.label} sx={{ mb: 1.25 }}>
          {!collapsed && (
            <Typography
              variant="caption"
              color={sidebarMuted}
              fontWeight={900}
              sx={{ display: 'block', px: 1.25, pt: 1.25, pb: 0.75, textTransform: 'uppercase', fontSize: '0.68rem' }}
            >
              {section.label}
            </Typography>
          )}
          {section.items.map((item) => {
            const Icon = item.icon;
            const selected = location.pathname.startsWith(item.path);
            const button = (
              <ListItemButton
                key={item.key}
                selected={selected}
                disabled={!item.enabled}
                onClick={() => {
                  if (item.enabled) navigate(item.path);
                  onNavigate?.();
                }}
                style={{ direction: 'rtl', textAlign: 'right' }}
                sx={{
                  borderRadius: 1,
                  mb: collapsed ? 0.75 : 0.35,
                  minHeight: collapsed ? 58 : 44,
                  width: collapsed ? 58 : '100%',
                  mx: collapsed ? 'auto' : 0,
                  display: 'flex',
                  flexDirection: collapsed ? 'column' : 'row',
                  alignItems: 'center',
                  justifyContent: collapsed ? 'center' : 'space-between',
                  gap: collapsed ? 0.35 : 1.25,
                  px: collapsed ? 0.5 : 1,
                  bgcolor: selected ? sidebarActiveBg : 'transparent',
                  color: selected ? sidebarActive : sidebarText,
                  '&.Mui-selected': {
                    bgcolor: sidebarActiveBg,
                    color: sidebarActive,
                  },
                  '&.Mui-selected:hover': { bgcolor: 'rgba(0, 167, 111, 0.12)' },
                  '&:hover': { bgcolor: 'rgba(145, 158, 171, 0.08)' },
                  '&.Mui-disabled': {
                    opacity: 1,
                    color: sidebarMuted,
                  },
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    minWidth: 0,
                    flex: collapsed ? 'initial' : 1,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    gap: collapsed ? 0 : 1.25,
                    color: selected ? sidebarActive : sidebarMuted,
                  }}
                >
                  <Icon fontSize={collapsed ? 'medium' : 'small'} />
                  {!collapsed && (
                    <Typography
                      fontSize="0.82rem"
                      fontWeight={selected ? 900 : 650}
                      lineHeight={1.35}
                      textAlign="right"
                      noWrap
                      sx={{ minWidth: 0, color: selected ? sidebarActive : sidebarText }}
                    >
                      {item.label}
                    </Typography>
                  )}
                </Box>
                {collapsed && (
                  <Typography fontSize="0.66rem" fontWeight={selected ? 900 : 750} noWrap maxWidth={50}>
                    {item.label}
                  </Typography>
                )}
                {!collapsed && !item.enabled && (
                  <ChevronLeft sx={{ fontSize: 17, color: sidebarMuted, flexShrink: 0 }} />
                )}
              </ListItemButton>
            );

            return collapsed ? (
              <Tooltip key={item.key} title={item.label} placement="left">
                <Box>{button}</Box>
              </Tooltip>
            ) : button;
          })}
        </Box>
      ))}
    </List>
  );
}

export function AppLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const mobileValue = useMemo(() => {
    const current = modules.find((item) => location.pathname.startsWith(item.path));
    return current?.path ?? '/vehicles';
  }, [location.pathname]);
  const activeDrawerWidth = sidebarCollapsed ? collapsedDrawerWidth : drawerWidth;

  return (
    <Box sx={{ direction: 'rtl', minHeight: '100vh', display: 'flex', pb: { xs: 8, md: 0 } }}>
      {!isMobile && (
        <Box
          component="aside"
          style={{
            position: 'fixed',
            top: 0,
            right: 0,
            bottom: 0,
            width: activeDrawerWidth,
            zIndex: theme.zIndex.drawer,
          }}
          sx={{
            width: activeDrawerWidth,
            borderLeft: '1px solid',
            borderColor: 'rgba(145, 158, 171, 0.16)',
            bgcolor: sidebarBg,
            overflowY: 'visible',
            boxShadow: '8px 0 24px rgba(20, 26, 33, 0.06)',
            transition: theme.transitions.create('width', { duration: theme.transitions.duration.shorter }),
          }}
        >
          <IconButton
            size="small"
            onClick={() => setSidebarCollapsed((current) => !current)}
            style={{
              position: 'absolute',
              left: -14,
              top: 24,
            }}
            sx={{
              width: 28,
              height: 28,
              bgcolor: sidebarBg,
              border: '1px solid',
              borderColor: 'rgba(145, 158, 171, 0.24)',
              color: sidebarText,
              boxShadow: '0 8px 18px rgba(0, 0, 0, 0.16)',
              zIndex: 2,
              '&:hover': { bgcolor: sidebarActiveBg, color: sidebarActive },
            }}
          >
            {sidebarCollapsed ? <ChevronLeft fontSize="small" /> : <ChevronRight fontSize="small" />}
          </IconButton>
          <Box px={sidebarCollapsed ? 1 : 2} py={2.25}>
            <BrandBlock compact={sidebarCollapsed} onDark />
          </Box>
          <Divider sx={{ borderColor: 'rgba(145, 158, 171, 0.12)' }} />
          <Box sx={{ height: 'calc(100vh - 81px)', overflowY: 'auto', overflowX: 'hidden' }}>
            <NavigationList collapsed={sidebarCollapsed} />
          </Box>
        </Box>
      )}

      <Box
        style={{
          ...(!isMobile ? { marginRight: activeDrawerWidth } : undefined),
          direction: 'rtl',
          textAlign: 'right',
        }}
        sx={{ flex: 1, minWidth: 0, transition: theme.transitions.create('margin-right', { duration: theme.transitions.duration.shorter }) }}
      >
        <AppBar
          position="sticky"
          color="inherit"
          elevation={0}
          sx={{ borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'rgba(255,255,255,0.86)', backdropFilter: 'blur(12px)' }}
        >
          <Toolbar sx={{ gap: 1, minHeight: { xs: 58, md: 66 } }}>
            {isMobile && (
              <IconButton edge="start" onClick={() => setDrawerOpen(true)}>
                <Menu />
              </IconButton>
            )}
            {isMobile ? <BrandBlock compact /> : <Box flex={1} />}
            <Box flex={1} />
            <Button
              size="small"
              variant="outlined"
              startIcon={<Logout />}
              onClick={() => {
                api.clearAuthTokens();
                navigate('/login', { replace: true });
              }}
              sx={{ display: { xs: 'none', sm: 'inline-flex' } }}
            >
              خروج
            </Button>
          </Toolbar>
        </AppBar>

        <Box
          component="main"
          style={{ direction: 'rtl', textAlign: 'right' }}
          sx={{
            p: { xs: 1.25, sm: 1.75, md: 2 },
            maxWidth: 1680,
            mx: 'auto',
          }}
        >
          <Outlet />
        </Box>
      </Box>

      {isMobile && (
        <>
          <Drawer
            anchor="right"
            open={drawerOpen}
            onClose={() => setDrawerOpen(false)}
            PaperProps={{ sx: { bgcolor: sidebarBg } }}
          >
            <Box width={292}>
              <Box p={2}>
                <BrandBlock onDark />
              </Box>
              <Divider sx={{ borderColor: 'rgba(145, 158, 171, 0.12)' }} />
              <NavigationList onNavigate={() => setDrawerOpen(false)} />
            </Box>
          </Drawer>
          <BottomNavigation
            value={mobileValue}
            onChange={(_, value: string) => navigate(value)}
            showLabels
            sx={{
              position: 'fixed',
              bottom: 0,
              right: 0,
              zIndex: theme.zIndex.appBar,
              borderTop: '1px solid',
              borderColor: 'divider',
            }}
          >
            {modules.filter((item) => item.enabled).map((item) => {
              const Icon = item.icon;
              return <BottomNavigationAction key={item.key} label={item.label} value={item.path} icon={<Icon />} />;
            })}
          </BottomNavigation>
        </>
      )}
    </Box>
  );
}

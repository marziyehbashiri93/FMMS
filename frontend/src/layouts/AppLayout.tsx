import { useEffect, useMemo, useState } from 'react';
import {
  AppBar,
  Avatar,
  Box,
  BottomNavigation,
  BottomNavigationAction,
  ButtonBase,
  Collapse,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Skeleton,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material';
import {
  ChevronLeft,
  ChevronRight,
  ExpandLess,
  ExpandMore,
  KeyboardArrowDown,
  Logout,
  Menu as MenuIcon,
  PersonOutline,
} from '@mui/icons-material';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useTheme } from '@mui/material/styles';
import { canAccessModule, navSectionsForUser } from '../app/access';
import { isNavGroup, modules, type AppModule, type NavGroup } from '../app/modules';
import { api } from '../api/client';
import { ProfileModal } from '../features/auth/ProfileModal';
import type { AuthUser } from '../types/fmms';

const drawerWidth = 244;
const collapsedDrawerWidth = 88;
const sidebarBg = '#141A21';
const sidebarText = '#919EAB';
const sidebarMuted = '#637381';
const sidebarActive = '#5BE49B';
const sidebarActiveBg = 'rgba(0, 167, 111, 0.08)';
const SIDEBAR_COLLAPSED_STORAGE_KEY = 'fmms.sidebarCollapsed';

function readSidebarCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function writeSidebarCollapsed(collapsed: boolean): void {
  try {
    localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, String(collapsed));
  } catch {
    // Ignore quota / private-mode failures; UI state still works in-session.
  }
}

const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'مدیر',
  SUPERVISOR: 'ناظر',
  TECHNICIAN: 'تکنسین',
  VIEWER: 'مشاهده‌گر',
};

function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role;
}

function profileInitials(user: AuthUser): string {
  const source = user.full_name.trim() || user.username.trim();
  if (!source) return '؟';
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`;
  return source.slice(0, 2);
}

function HeaderProfileMenu({
  user,
  loading,
  onProfile,
  onLogout,
}: {
  user: AuthUser | null;
  loading: boolean;
  onProfile: () => void;
  onLogout: () => void;
}) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);

  if (loading) {
    return (
      <Stack direction="row" alignItems="center" spacing={1.25} minWidth={0}>
        <Skeleton variant="circular" width={40} height={40} />
        <Box minWidth={0} sx={{ display: { xs: 'none', sm: 'block' } }}>
          <Skeleton width={120} height={16} sx={{ mb: 0.5 }} />
          <Skeleton width={72} height={12} />
        </Box>
      </Stack>
    );
  }

  if (!user) return null;

  const displayName = user.full_name.trim() || user.username;

  return (
    <>
      <ButtonBase
        onClick={(event) => setAnchorEl(event.currentTarget)}
        aria-haspopup="menu"
        aria-expanded={open ? 'true' : undefined}
        aria-controls={open ? 'header-profile-menu' : undefined}
        sx={{
          borderRadius: (t) => t.radius('md'),
          px: 0.75,
          py: 0.5,
          gap: 1,
          '&:hover': { bgcolor: 'rgba(0, 167, 111, 0.06)' },
        }}
      >
        <Avatar
          sx={{
            width: 40,
            height: 40,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            fontWeight: 800,
            fontSize: '0.85rem',
          }}
        >
          {profileInitials(user)}
        </Avatar>
        <Box minWidth={0} textAlign="right" sx={{ display: { xs: 'none', sm: 'block' } }}>
          <Typography fontWeight={800} noWrap fontSize="0.9rem" lineHeight={1.3}>
            {displayName}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap display="block">
            {roleLabel(user.role)}
          </Typography>
        </Box>
        <KeyboardArrowDown
          sx={{
            color: 'text.secondary',
            fontSize: 20,
            display: { xs: 'none', sm: 'block' },
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.15s ease',
          }}
        />
      </ButtonBase>

      <Menu
        id="header-profile-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        disableScrollLock
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        transformOrigin={{ vertical: 'top', horizontal: 'left' }}
        slotProps={{
          paper: {
            sx: {
              mt: 1,
              minWidth: 200,
              borderRadius: (t) => t.radius('md'),
              border: '1px solid',
              borderColor: 'divider',
              direction: 'rtl',
            },
          },
        }}
      >
        <MenuItem
          onClick={() => {
            setAnchorEl(null);
            onProfile();
          }}
        >
          <ListItemIcon sx={{ minWidth: 36 }}>
            <PersonOutline fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="پروفایل" />
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            setAnchorEl(null);
            onLogout();
          }}
          sx={{ color: 'error.main' }}
        >
          <ListItemIcon sx={{ minWidth: 36, color: 'error.main' }}>
            <Logout fontSize="small" />
          </ListItemIcon>
          <ListItemText primary="خروج" />
        </MenuItem>
      </Menu>
    </>
  );
}

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
          borderRadius: (t) => t.radius('lg'),
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

const navItemSx = (selected: boolean, collapsed: boolean) =>
  ({
    borderRadius: (t: { radius: (token: 'xs' | 'sm' | 'md' | 'lg' | 'xl') => string }) => t.radius('md'),
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
  }) as const;

function NavLeafButton({
  item,
  collapsed,
  nested = false,
  onNavigate,
}: {
  item: AppModule;
  collapsed: boolean;
  nested?: boolean;
  onNavigate?: () => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const Icon = item.icon;
  const selected = location.pathname.startsWith(item.path);

  const button = (
    <ListItemButton
      selected={selected}
      disabled={!item.enabled}
      onClick={() => {
        if (item.enabled) navigate(item.path);
        onNavigate?.();
      }}
      style={{ direction: 'rtl', textAlign: 'right' }}
      sx={{
        ...navItemSx(selected, collapsed),
        ...(nested && !collapsed ? { pr: 1, pl: 1.5, minHeight: 40 } : {}),
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
            fontSize={nested ? '0.78rem' : '0.82rem'}
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
    <Tooltip title={item.label} placement="left">
      <Box>{button}</Box>
    </Tooltip>
  ) : (
    button
  );
}

function NavGroupItem({
  group,
  collapsed,
  onNavigate,
}: {
  group: NavGroup;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const location = useLocation();
  const navigate = useNavigate();
  const childActive = group.children.some((child) => location.pathname.startsWith(child.path));
  const [open, setOpen] = useState(childActive);
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const GroupIcon = group.icon;

  useEffect(() => {
    if (childActive) setOpen(true);
  }, [childActive]);

  if (collapsed) {
    return (
      <>
        <Tooltip title={group.label} placement="left">
          <Box>
            <ListItemButton
              selected={childActive}
              onClick={(event) => setMenuAnchor(event.currentTarget)}
              style={{ direction: 'rtl', textAlign: 'right' }}
              sx={navItemSx(childActive, true)}
            >
              <Box sx={{ color: childActive ? sidebarActive : sidebarMuted, display: 'flex' }}>
                <GroupIcon fontSize="medium" />
              </Box>
              <Typography fontSize="0.66rem" fontWeight={childActive ? 900 : 750} noWrap maxWidth={50}>
                {group.label}
              </Typography>
            </ListItemButton>
          </Box>
        </Tooltip>
        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={() => setMenuAnchor(null)}
          anchorOrigin={{ vertical: 'top', horizontal: 'left' }}
          transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          disableScrollLock
        >
          {group.children.map((child) => {
            const ChildIcon = child.icon;
            const selected = location.pathname.startsWith(child.path);
            return (
              <MenuItem
                key={child.key}
                selected={selected}
                disabled={!child.enabled}
                onClick={() => {
                  if (child.enabled) navigate(child.path);
                  setMenuAnchor(null);
                  onNavigate?.();
                }}
              >
                <ListItemIcon sx={{ minWidth: 36, color: selected ? 'primary.main' : 'inherit' }}>
                  <ChildIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText primary={child.label} />
              </MenuItem>
            );
          })}
        </Menu>
      </>
    );
  }

  return (
    <Box>
      <ListItemButton
        selected={childActive && !open}
        onClick={() => setOpen((prev) => !prev)}
        style={{ direction: 'rtl', textAlign: 'right' }}
        sx={navItemSx(childActive, false)}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            minWidth: 0,
            flex: 1,
            gap: 1.25,
            color: childActive ? sidebarActive : sidebarMuted,
          }}
        >
          <GroupIcon fontSize="small" />
          <Typography
            fontSize="0.82rem"
            fontWeight={childActive ? 900 : 650}
            lineHeight={1.35}
            textAlign="right"
            noWrap
            sx={{ minWidth: 0, color: childActive ? sidebarActive : sidebarText }}
          >
            {group.label}
          </Typography>
        </Box>
        {open ? (
          <ExpandLess sx={{ fontSize: 18, color: sidebarMuted, flexShrink: 0 }} />
        ) : (
          <ExpandMore sx={{ fontSize: 18, color: sidebarMuted, flexShrink: 0 }} />
        )}
      </ListItemButton>
      <Collapse in={open} timeout="auto" unmountOnExit>
        <List disablePadding sx={{ pr: 1.25, pb: 0.5 }}>
          {group.children.map((child) => (
            <NavLeafButton key={child.key} item={child} collapsed={false} nested onNavigate={onNavigate} />
          ))}
        </List>
      </Collapse>
    </Box>
  );
}

function NavigationList({
  user,
  collapsed = false,
  onNavigate,
}: {
  user: AuthUser | null;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const sections = useMemo(() => navSectionsForUser(user), [user]);
  return (
    <List disablePadding sx={{ px: collapsed ? 1 : 1.5, py: 1.5 }}>
      {sections.map((section) => (
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
          {section.entries.map((entry) =>
            isNavGroup(entry) ? (
              <NavGroupItem key={entry.key} group={entry} collapsed={collapsed} onNavigate={onNavigate} />
            ) : (
              <NavLeafButton key={entry.key} item={entry} collapsed={collapsed} onNavigate={onNavigate} />
            ),
          )}
        </Box>
      ))}
    </List>
  );
}

export function AppLayout() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(readSidebarCollapsed);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const mobileValue = useMemo(() => {
    const current = modules.find((item) => location.pathname.startsWith(item.path));
    return current?.path ?? '/dashboard';
  }, [location.pathname]);
  const activeDrawerWidth = sidebarCollapsed ? collapsedDrawerWidth : drawerWidth;

  useEffect(() => {
    writeSidebarCollapsed(sidebarCollapsed);
  }, [sidebarCollapsed]);

  useEffect(() => {
    let cancelled = false;
    setProfileLoading(true);
    void api
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setProfileLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogout = () => {
    api.clearAuthTokens();
    navigate('/login', { replace: true });
  };

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
            <NavigationList user={user} collapsed={sidebarCollapsed} />
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
          <Toolbar sx={{ gap: 1.25, minHeight: { xs: 58, md: 66 } }}>
            {isMobile && (
              <IconButton edge="start" onClick={() => setDrawerOpen(true)} aria-label="منو">
                <MenuIcon />
              </IconButton>
            )}
            <Box flex={1} />
            <HeaderProfileMenu
              user={user}
              loading={profileLoading}
              onProfile={() => setProfileModalOpen(true)}
              onLogout={handleLogout}
            />
          </Toolbar>
        </AppBar>

        <ProfileModal
          open={profileModalOpen}
          onClose={() => setProfileModalOpen(false)}
          initialUser={user}
        />

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
              <NavigationList user={user} onNavigate={() => setDrawerOpen(false)} />
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
            {modules
              .filter((item) => item.enabled && canAccessModule(user, item.key))
              .map((item) => {
              const Icon = item.icon;
              return <BottomNavigationAction key={item.key} label={item.label} value={item.path} icon={<Icon />} />;
            })}
          </BottomNavigation>
        </>
      )}
    </Box>
  );
}

import createCache from '@emotion/cache';
import { CacheProvider } from '@emotion/react';
import { CssBaseline, GlobalStyles } from '@mui/material';
import { createTheme, ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import type { ReactNode } from 'react';

const cacheRtl = createCache({
  key: 'fmms-rtl',
});

export const theme = createTheme({
  direction: 'rtl',
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: 'Vazirmatn, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: { fontWeight: 800, fontSize: '1.45rem', lineHeight: 1.35 },
    h2: { fontWeight: 800, fontSize: '1.25rem', lineHeight: 1.4 },
    h3: { fontWeight: 750, fontSize: '1.05rem', lineHeight: 1.45 },
    button: { fontWeight: 700 },
  },
  palette: {
    mode: 'light',
    primary: {
      main: '#00A76F',
      light: '#D3FCD2',
      dark: '#007867',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#8d6b1f',
      light: '#f1ead8',
      dark: '#5f4712',
      contrastText: '#111827',
    },
    success: { main: '#248a57' },
    warning: { main: '#d28a20' },
    error: { main: '#c94132' },
    info: { main: '#2d6f95' },
    background: {
      default: '#f4f6f8',
      paper: '#ffffff',
    },
    text: {
      primary: '#17231d',
      secondary: '#607067',
    },
    divider: '#dde5e0',
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 8, textTransform: 'none', minHeight: 36 },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          right: 14,
          left: 'auto',
          transformOrigin: 'top right',
          textAlign: 'right',
        },
      },
    },
    MuiFormControl: {
      defaultProps: { size: 'small' },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {},
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          border: '1px solid #dfe5da',
          boxShadow: '0 10px 28px rgba(31, 79, 57, 0.07)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 6, fontWeight: 700 },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none' },
      },
    },
    MuiTable: {
      defaultProps: {
        dir: 'rtl !important',
      },
      styleOverrides: {
        root: { direction: 'rtl' },
      },
    },
    MuiTableContainer: {
      defaultProps: {
        dir: 'inherit',
      },
      styleOverrides: {
        root: { direction: 'rtl' },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #d3ddd8',
          textAlign: 'right',
        },
        head: {
          backgroundColor: '#eef4f1',
          color: '#31453a',
          fontWeight: 900,
          borderBottom: '1px solid #cad8d1',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:nth-of-type(even) td': {
            backgroundColor: 'rgba(20, 26, 33, 0.018)',
          },
          '&:hover td': {
            backgroundColor: 'rgba(0, 167, 111, 0.045)',
          },
        },
      },
    },
    MuiTableSortLabel: {
      styleOverrides: {
        root: {
          color: '#31453a',
          fontWeight: 900,
          '&.Mui-active': { color: '#155f3d' },
          '& .MuiTableSortLabel-icon': { color: '#155f3d !important' },
        },
      },
    },
  },
});

export function ThemeProvider({ children }: { children: ReactNode }) {
  return (
    <CacheProvider value={cacheRtl}>
      <MuiThemeProvider theme={theme}>
        <CssBaseline />
        <GlobalStyles
          styles={{
            html: { direction: 'rtl !important' },
            ':root': {
              '--palette-primary-mainChannel': '0 167 111',
            },
            body: {
              direction: 'rtl !important',
              minWidth: 320,
              background: '#f4f6f8',
            },
            '#root': { minHeight: '100vh',      direction: 'rtl !important' },
            '*': { boxSizing: 'border-box' },
          }}
        />
        <div dir="rtl">{children}</div>
      </MuiThemeProvider>
    </CacheProvider>
  );
}

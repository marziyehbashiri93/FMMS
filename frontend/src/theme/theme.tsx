import createCache from '@emotion/cache';
import {CacheProvider} from '@emotion/react';
import {CssBaseline, GlobalStyles} from '@mui/material';
import {createTheme, ThemeProvider as MuiThemeProvider} from '@mui/material/styles';
import type {ReactNode} from 'react';
import {radii} from './radii';

export {radii, radiusPx} from './radii';
export type {Radii, RadiusToken} from './radii';

const cacheRtl = createCache({
    key: 'fmms-rtl',
});

export const theme = createTheme({
    direction: 'rtl',
    shape: {borderRadius: radii.md},
    radii,
    typography: {
        fontFamily: 'Vazirmatn, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        h1: {fontWeight: 800, fontSize: '1.45rem', lineHeight: 1.35},
        h2: {fontWeight: 800, fontSize: '1.25rem', lineHeight: 1.4},
        h3: {fontWeight: 700, fontSize: '1.05rem', lineHeight: 1.45},
        button: {fontWeight: 700},
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
            main: '#1565C0',
            light: '#d6e4f7',
            dark: '#0d47a1',
            contrastText: '#ffffff',
        },
        success: {
            main: '#248a57',
            light: '#d3f5e3',
            dark: '#1a6640',
            contrastText: '#ffffff',
        },
        warning: {
            main: '#F59E0B',
            light: '#fef3c7',
            dark: '#b45309',
            contrastText: '#ffffff',
        },
        error: {
            main: '#EF4444',
            light: '#fee2e2',
            dark: '#b91c1c',
            contrastText: '#ffffff',
        },
        info: {
            main: '#2d6f95',
            light: '#daeef8',
            dark: '#1f5070',
            contrastText: '#ffffff',
        },
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
            defaultProps: {disableElevation: true},
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    textTransform: 'none',
                    minHeight: 36,
                }),
            },
        },
        MuiTextField: {
            defaultProps: {size: 'small'},
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
            defaultProps: {size: 'small'},
        },
        MuiOutlinedInput: {
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                }),
                notchedOutline: {
                    textAlign: 'right',
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    border: '1px solid #dfe5da',
                    boxShadow: '0 10px 28px rgba(31, 79, 57, 0.07)',
                }),
            },
        },
        MuiChip: {
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.sm,
                    fontWeight: 700,
                }),
            },
        },
        MuiDialog: {
            styleOverrides: {
                paper: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                }),
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {backgroundImage: 'none'},
                rounded: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                }),
            },
        },
        MuiTable: {
            defaultProps: {
                dir: 'rtl !important',
            },
            styleOverrides: {
                root: {direction: 'rtl'},
            },
        },
        MuiTableContainer: {
            defaultProps: {
                dir: 'inherit',
            },
            styleOverrides: {
                root: {direction: 'rtl'},
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
                    '&.Mui-active': {color: '#155f3d'},
                    '& .MuiTableSortLabel-icon': {color: '#155f3d !important'},
                },
            },
        },
    },
});

// sx multiplies unitless borderRadius by shape.borderRadius — always use px strings there.
theme.radius = (token) => `${theme.radii[token]}px`;

export function ThemeProvider({children}: { children: ReactNode }) {
    return (
        <CacheProvider value={cacheRtl}>
            <MuiThemeProvider theme={theme}>
                <CssBaseline/>
                <GlobalStyles
                    styles={(t) => ({
                        html: {
                            direction: 'rtl !important',
                            scrollbarGutter: 'stable',
                        },
                        ':root': {
                            '--palette-primary-mainChannel': '0 167 111',
                            '--fmms-radius-xs': `${t.radii.xs}px`,
                            '--fmms-radius-sm': `${t.radii.sm}px`,
                            '--fmms-radius-md': `${t.radii.md}px`,
                            '--fmms-radius-lg': `${t.radii.lg}px`,
                            '--fmms-radius-xl': `${t.radii.xl}px`,
                        },
                        body: {
                            direction: 'rtl !important',
                            minWidth: 320,
                            background: '#f4f6f8',
                        },
                        // Prevent MUI Modal scroll-lock padding from shifting fixed sidebar in RTL
                        'body[data-scroll-locked]': {
                            paddingLeft: '0 !important',
                            paddingRight: '0 !important',
                            marginLeft: '0 !important',
                            marginRight: '0 !important',
                        },
                        '#root': {minHeight: '100vh', direction: 'rtl !important'},
                        '*': {boxSizing: 'border-box'},
                    })}
                />
                <div dir="rtl">{children}</div>
            </MuiThemeProvider>
        </CacheProvider>
    );
}

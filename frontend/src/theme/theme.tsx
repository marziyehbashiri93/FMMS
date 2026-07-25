import createCache from '@emotion/cache';
import {CacheProvider} from '@emotion/react';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import WarningIcon from '@mui/icons-material/Warning';
import {CssBaseline, GlobalStyles} from '@mui/material';
import {createTheme, ThemeProvider as MuiThemeProvider} from '@mui/material/styles';
import type {ReactNode} from 'react';
import {createElement} from 'react';
import {radii} from './radii';

export {radii, radiusPx} from './radii';
export type {Radii, RadiusToken} from './radii';

const cacheRtl = createCache({
    key: 'fmms-rtl',
});

export const theme = createTheme({
    direction: 'rtl',

    shape: {
        borderRadius: radii.md,
    },

    radii,

    typography: {
        fontFamily:
            'Vazirmatn, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',

        h1: {
            fontWeight: 800,
            fontSize: '1.55rem',
            lineHeight: 1.3,
            letterSpacing: '-0.02em',
            color: '#17231D',
        },

        h2: {
            fontWeight: 700,
            fontSize: '1.30rem',
            lineHeight: 1.35,
            letterSpacing: '-0.01em',
            color: '#17231D',
        },

        h3: {
            fontWeight: 700,
            fontSize: '1.10rem',
            lineHeight: 1.45,
            color: '#1F3D32',
        },

        h4: {
            fontWeight: 700,
            fontSize: '1rem',
            lineHeight: 1.5,
            color: '#1F3D32',
        },

        h5: {
            fontWeight: 600,
            fontSize: '.95rem',
            lineHeight: 1.5,
            color: '#0F6B4C',
        },

        h6: {
            fontWeight: 600,
            fontSize: '.90rem',
            lineHeight: 1.5,
            color: '#0F6B4C',
        },

        body1: {
            fontSize: '.95rem',
            lineHeight: 1.7,
            color: '#17231D',
        },

        body2: {
            fontSize: '.875rem',
            lineHeight: 1.6,
            color: '#5A6B63',
        },

        button: {
            fontWeight: 700,
            fontSize: '.9rem',
            textTransform: 'none',
        },

        subtitle1: {
            fontWeight: 600,
            color: '#1F3D32',
        },

        subtitle2: {
            fontWeight: 600,
            color: '#5A6B63',
        },

        caption: {
            color: '#5A6B63',
        },
    },
    palette: {
        mode: 'light',

        // Brand green (~80% of UI chrome)
        primary: {
            main: '#0F6B4C',
            light: '#D8F0E5',
            dark: '#0A4D37',
            contrastText: '#FFFFFF',
        },

        // Golestan copper/red accent (~20% emphasis)
        secondary: {
            main: '#C45C4A',
            light: '#f3e5e1',
            dark: '#9E3F31',
            contrastText: '#FFFFFF',
        },

        success: {
            main: '#248A57',
            light: '#D7F3E4',
            dark: '#155F3D',
            contrastText: '#FFFFFF',
        },

        warning: {
            main: '#D28A20',
            light: '#FFF1D6',
            dark: '#9A6410',
            contrastText: '#FFFFFF',
        },

        error: {
            main: '#C94132',
            light: '#FDE4E1',
            dark: '#9F2F27',
            contrastText: '#FFFFFF',
        },

        info: {
            main: '#2D6F95',
            light: '#DCEEF8',
            dark: '#1F5070',
            contrastText: '#FFFFFF',
        },

        background: {
            default: '#F3F6F4',
            paper: '#FFFFFF',
        },

        text: {
            primary: '#17231D',
            secondary: '#5A6B63',
            disabled: '#9AABA3',
        },

        divider: '#D5E0DA',

        action: {
            hover: 'rgba(15,107,76,.08)',
            selected: 'rgba(15,107,76,.12)',
            disabled: 'rgba(23,35,29,.30)',
            disabledBackground: '#EAF0EC',
            focus: 'rgba(15,107,76,.18)',
        },
    },
    components: {
        MuiButton: {
            defaultProps: {
                disableElevation: true,
            },
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    textTransform: 'none',
                    minHeight: 38,
                    fontWeight: 700,
                    paddingInline: 18,
                    transition: 'all .2s ease',
                }),

                containedPrimary: {
                    backgroundColor: '#0F6B4C',

                    '&:hover': {
                        backgroundColor: '#0A4D37',
                    },
                },

                containedSecondary: {
                    backgroundColor: '#C45C4A',

                    '&:hover': {
                        backgroundColor: '#9E3F31',
                    },
                },

                outlinedPrimary: {
                    borderColor: '#0F6B4C',
                    color: '#0F6B4C',

                    '&:hover': {
                        borderColor: '#0A4D37',
                        backgroundColor: 'rgba(15,107,76,.06)',
                    },
                },

                outlinedSecondary: {
                    borderColor: '#C45C4A',
                    color: '#9E3F31',

                    '&:hover': {
                        borderColor: '#9E3F31',
                        backgroundColor: 'rgba(196,92,74,.08)',
                    },
                },
            },
        },
        MuiTextField: {
            defaultProps: {
                size: 'small',
                variant: 'outlined',
            },
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
                    transition: '.2s',

                    '&:hover .MuiOutlinedInput-notchedOutline': {
                        borderColor: '#0F6B4C',
                    },

                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                        borderColor: '#0A4D37',
                        borderWidth: 2,
                    },
                }),

                notchedOutline: {
                    textAlign: 'right',
                    borderColor: '#D5E0DA',
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    border: '1px solid #DDE7E1',
                    boxShadow: '0 6px 18px rgba(15,107,76,.07)',
                    overflow: 'hidden',
                }),
            },
        },
        MuiChip: {
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.sm,
                    fontWeight: 700,
                    paddingInline: 6,
                }),
                colorPrimary: {
                    backgroundColor: 'rgba(15,107,76,.12)',
                    color: '#0A4D37',
                },
                colorSecondary: {
                    backgroundColor: 'rgba(196,92,74,.14)',
                    color: '#9E3F31',
                },
            },
        },
        MuiTab: {
            styleOverrides: {
                root: {
                    fontWeight: 700,
                    '&.Mui-selected': {
                        color: '#0F6B4C',
                    },
                },
            },
        },
        MuiTabs: {
            styleOverrides: {
                indicator: {
                    // Accent only — keep selected label primary green.
                    backgroundColor: '#C45C4A',
                    height: 3,
                    borderRadius: 999,
                },
            },
        },
        MuiDialog: {
            defaultProps: {
                disableScrollLock: true,
            },
            styleOverrides: {
                // Blur only for Dialogs — not Select/Menu/Popover overlays.
                root: {
                    '& > .MuiBackdrop-root': {
                        backgroundColor: 'rgba(23, 35, 29, 0.42)',
                        backdropFilter: 'blur(0.5px)',
                        WebkitBackdropFilter: 'blur(0.5px)',
                    },
                },
                paper: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    boxShadow: '0 18px 40px rgba(15, 107, 76, 0.16)',
                    maxHeight: '85vh',
                }),
            },
        },
        MuiModal: {
            defaultProps: {
                disableScrollLock: true,
            },
        },
        MuiPopover: {
            defaultProps: {
                disableScrollLock: true,
            },
        },
        MuiMenu: {
            defaultProps: {
                disableScrollLock: true,
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    backgroundImage: 'none',
                    border: '1px solid #E8EFEA',
                },

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
                    borderBottom: '1px solid #D5E0DA',
                    textAlign: 'right',
                    paddingTop: 14,
                    paddingBottom: 14,
                },

                head: {
                    backgroundColor: '#EAF5EF',
                    color: '#1F3D32',
                    fontWeight: 800,
                    borderBottom: '1px solid #D5E0DA',
                },
            },
        },
        MuiTableRow: {
            styleOverrides: {
                root: {

                    transition: '.15s',

                    '&:nth-of-type(even) td': {
                        backgroundColor: 'rgba(15,107,76,.03)',
                    },

                    '&:hover td': {
                        backgroundColor: 'rgba(15,107,76,.07)',
                    },
                },
            },
        },
        MuiTableSortLabel: {
            styleOverrides: {
                root: {
                    // Sortable but inactive: same weight as header, no visible arrow.
                    color: '#1F3D32',
                    fontWeight: 700,

                    '&:hover': {
                        color: '#0F6B4C',
                        '& .MuiTableSortLabel-icon': {
                            opacity: 0.45,
                            color: '#6B8A7A',
                        },
                    },

                    // Only the active sort column shows a strong arrow + brand color.
                    '&.Mui-active': {
                        color: '#0F6B4C',
                        fontWeight: 800,

                        '& .MuiTableSortLabel-icon': {
                            opacity: 1,
                            color: '#0F6B4C',
                        },
                    },
                },
                icon: {
                    color: '#6B8A7A',
                },
            },
        },
        MuiAlert: {
            defaultProps: {
                iconMapping: {
                    // Filled circle with "!" for info notices (clearer than outlined "i").
                    info: createElement(ErrorIcon, {fontSize: 'inherit'}),
                    success: createElement(CheckCircleIcon, {fontSize: 'inherit'}),
                    warning: createElement(WarningIcon, {fontSize: 'inherit'}),
                    error: createElement(ErrorIcon, {fontSize: 'inherit'}),
                },
            },
            styleOverrides: {
                root: {
                    alignItems: 'center',
                    '& .MuiAlert-icon': {
                        marginInlineEnd: 12,
                        marginInlineStart: 0,
                        alignSelf: 'center',
                        padding: '5px 0',
                    },
                    '& .MuiAlert-message': {
                        padding: '5px 0',
                        lineHeight: 1.5,
                    },
                },
                standardInfo: ({theme: t}) => ({
                    backgroundColor: t.palette.info.light,
                    color: t.palette.info.dark,
                    border: `1px solid ${t.palette.info.main}33`,
                    flexWrap: 'nowrap',
                    '& .MuiAlert-icon': {
                        color: t.palette.info.main,
                    },
                    '& .MuiAlert-message': {
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                    },
                }),
                standardError: ({theme: t}) => ({
                    backgroundColor: t.palette.error.light,
                    color: t.palette.error.dark,
                    border: `1px solid ${t.palette.error.main}40`,
                    '& .MuiAlert-icon': {
                        color: t.palette.error.main,
                        marginInlineEnd: 16,
                    },
                    '& .MuiAlert-action': {
                        marginInlineEnd: 0,
                        marginInlineStart: 12,
                        paddingTop: 0,
                        alignItems: 'center',
                    },
                }),
            },
        },
        MuiTooltip: {
            styleOverrides: {
                tooltip: {
                    borderRadius: 8,
                    fontSize: '.8rem',
                },
            },
        },
        MuiDivider: {
            styleOverrides: {
                root: {
                    borderColor: '#D5E0DA',
                },
            },
        },
    },
});

// sx multiplies unitless borderRadius by shape.borderRadius — always use px strings there.
theme.radius = (token) => `${theme.radii[token]}px`;

export function ThemeProvider({ children }: { children: ReactNode }) {
    return (
        <CacheProvider value={cacheRtl}>
            <MuiThemeProvider theme={theme}>
                <CssBaseline />

                <GlobalStyles
                    styles={(t) => ({
                        html: {
                            direction: 'rtl',
                            scrollbarGutter: 'stable',
                            overflowY: 'scroll',
                            scrollBehavior: 'smooth',
                            WebkitFontSmoothing: 'antialiased',
                            MozOsxFontSmoothing: 'grayscale',
                        },

                        ':root': {
                            '--palette-primary-mainChannel': '15 107 76',
                            '--palette-secondary-mainChannel': '196 92 74',

                            '--fmms-radius-xs': `${t.radii.xs}px`,
                            '--fmms-radius-sm': `${t.radii.sm}px`,
                            '--fmms-radius-md': `${t.radii.md}px`,
                            '--fmms-radius-lg': `${t.radii.lg}px`,
                            '--fmms-radius-xl': `${t.radii.xl}px`,
                        },

                        body: {
                            direction: 'rtl',
                            minWidth: 320,
                            margin: 0,
                            padding: 0,

                            background: t.palette.background.default,
                            color: t.palette.text.primary,

                            fontFamily: t.typography.fontFamily,

                            textRendering: 'optimizeLegibility',
                            WebkitFontSmoothing: 'antialiased',
                            MozOsxFontSmoothing: 'grayscale',
                        },

                        a: {
                            color: 'inherit',
                            textDecoration: 'none',
                        },

                        img: {
                            maxWidth: '100%',
                            display: 'block',
                        },

                        '*': {
                            boxSizing: 'border-box',
                        },

                        '*, *::before, *::after': {
                            boxSizing: 'inherit',
                        },

                        '#root': {
                            minHeight: '100vh',
                            direction: 'rtl',
                            display: 'flex',
                            flexDirection: 'column',
                        },

                        // جلوگیری از پرش هنگام باز شدن Dialog و Drawer
                        'body[data-scroll-locked], html[data-scroll-locked]': {
                            paddingLeft: '0 !important',
                            paddingRight: '0 !important',
                            marginLeft: '0 !important',
                            marginRight: '0 !important',
                            '--removed-body-scroll-bar-size': '0px',
                        },

                        'body[style*="padding-right"], body[style*="padding-left"]': {
                            paddingLeft: '0 !important',
                            paddingRight: '0 !important',
                        },

                        // Scrollbar (فقط مرورگرهای WebKit)
                        '*::-webkit-scrollbar': {
                            width: 10,
                            height: 10,
                        },

                        '*::-webkit-scrollbar-track': {
                            background: '#EAF0EC',
                        },

                        '*::-webkit-scrollbar-thumb': {
                            background: '#8FB9A5',
                            borderRadius: 999,
                            border: '2px solid #EAF0EC',
                        },

                        '*::-webkit-scrollbar-thumb:hover': {
                            background: '#0F6B4C',
                        },

                        '::selection': {
                            background: 'rgba(15,107,76,.22)',
                            color: '#17231D',
                        },
                    })}
                />

                <div dir="rtl">
                    {children}
                </div>
            </MuiThemeProvider>
        </CacheProvider>
    );
}
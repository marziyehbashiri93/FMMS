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
            color: '#334547',
        },

        h2: {
            fontWeight: 700,
            fontSize: '1.30rem',
            lineHeight: 1.35,
            letterSpacing: '-0.01em',
            color: '#334547',
        },

        h3: {
            fontWeight: 700,
            fontSize: '1.10rem',
            lineHeight: 1.45,
            color: '#35585D',
        },

        h4: {
            fontWeight: 700,
            fontSize: '1rem',
            lineHeight: 1.5,
            color: '#35585D',
        },

        h5: {
            fontWeight: 600,
            fontSize: '.95rem',
            lineHeight: 1.5,
            color: '#4F7D83',
        },

        h6: {
            fontWeight: 600,
            fontSize: '.90rem',
            lineHeight: 1.5,
            color: '#4F7D83',
        },

        body1: {
            fontSize: '.95rem',
            lineHeight: 1.7,
            color: '#334547',
        },

        body2: {
            fontSize: '.875rem',
            lineHeight: 1.6,
            color: '#6B7C80',
        },

        button: {
            fontWeight: 700,
            fontSize: '.9rem',
            textTransform: 'none',
        },

        subtitle1: {
            fontWeight: 600,
            color: '#35585D',
        },

        subtitle2: {
            fontWeight: 600,
            color: '#6B7C80',
        },

        caption: {
            color: '#6B7C80',
        },
    },
    palette: {
        mode: 'light',

        primary: {
            main: '#6E9EA2',
            light: '#95C6C2',
            dark: '#4F7D83',
            contrastText: '#FFFFFF',
        },

        secondary: {
            main: '#E7A699',
            light: '#F6D7D1',
            dark: '#CF8678',
            contrastText: '#FFFFFF',
        },

        success: {
            main: '#2E7D32',
            light: '#DFF3E2',
            dark: '#1B5E20',
            contrastText: '#FFFFFF',
        },

        warning: {
            main: '#ED8B00',
            light: '#FFF2D9',
            dark: '#B25E00',
            contrastText: '#FFFFFF',
        },

        error: {
            main: '#D84343',
            light: '#FDE5E5',
            dark: '#A62828',
            contrastText: '#FFFFFF',
        },

        info: {
            main: '#4F7D83',
            light: '#E2EFF0',
            dark: '#35585D',
            contrastText: '#FFFFFF',
        },

        background: {
            default: '#F6F8F8',
            paper: '#FFFFFF',
        },

        text: {
            primary: '#334547',
            secondary: '#6B7C80',
            disabled: '#9AA8AA',
        },

        divider: '#D9E3E4',

        action: {
            hover: 'rgba(110,158,162,.08)',
            selected: 'rgba(110,158,162,.14)',
            disabled: 'rgba(51,69,71,.30)',
            disabledBackground: '#EEF2F2',
            focus: 'rgba(110,158,162,.18)',
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
                    backgroundColor: '#6E9EA2',

                    '&:hover': {
                        backgroundColor: '#4F7D83',
                    },
                },

                containedSecondary: {
                    backgroundColor: '#E7A699',

                    '&:hover': {
                        backgroundColor: '#CF8678',
                    },
                },

                outlinedPrimary: {
                    borderColor: '#95C6C2',

                    '&:hover': {
                        borderColor: '#4F7D83',
                        backgroundColor: 'rgba(110,158,162,.05)',
                    },
                },

                outlinedSecondary: {
                    borderColor: '#E7A699',
                    color: '#CF8678',

                    '&:hover': {
                        borderColor: '#CF8678',
                        backgroundColor: 'rgba(231,166,153,.08)',
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
                        borderColor: '#95C6C2',
                    },

                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                        borderColor: '#4F7D83',
                        borderWidth: 2,
                    },
                }),

                notchedOutline: {
                    textAlign: 'right',
                    borderColor: '#D8E2E3',
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    border: '1px solid #E6ECEC',
                    boxShadow: '0 6px 18px rgba(79,125,131,.08)',
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
                    backgroundColor: 'rgba(110,158,162,.14)',
                    color: '#4F7D83',
                },
                colorSecondary: {
                    backgroundColor: 'rgba(231,166,153,.18)',
                    color: '#CF8678',
                },
            },
        },
        MuiTab: {
            styleOverrides: {
                root: {
                    fontWeight: 700,
                    '&.Mui-selected': {
                        color: '#4F7D83',
                    },
                },
            },
        },
        MuiTabs: {
            styleOverrides: {
                indicator: {
                    backgroundColor: '#E7A699',
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
                paper: ({theme: t}) => ({
                    borderRadius: t.radii.md,
                    boxShadow: '0 18px 40px rgba(0,0,0,.12)',

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
                    border: '1px solid #EDF2F2',
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
                    borderBottom: '1px solid #D9E3E4',
                    textAlign: 'right',
                    paddingTop: 14,
                    paddingBottom: 14,
                },

                head: {
                    backgroundColor: '#EEF7F6',
                    color: '#35585D',
                    fontWeight: 800,
                    borderBottom: '1px solid #D9E3E4',
                },
            },
        },
        MuiTableRow: {
            styleOverrides: {
                root: {

                    transition: '.15s',

                    '&:nth-of-type(even) td': {
                        backgroundColor: 'rgba(79,125,131,.025)',
                    },

                    '&:hover td': {
                        backgroundColor: 'rgba(231,166,153,.10)',
                    },
                },
            },
        },
        MuiTableSortLabel: {
            styleOverrides: {
                root: {
                    color: '#35585D',
                    fontWeight: 800,

                    '&.Mui-active': {
                        color: '#CF8678',
                    },

                    '& .MuiTableSortLabel-icon': {
                        color: '#CF8678 !important',
                    },
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
                    borderColor: '#D9E3E4',
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
                            '--palette-primary-mainChannel': '110 158 162',
                            '--palette-secondary-mainChannel': '231 166 153',

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
                            background: '#EDF3F3',
                        },

                        '*::-webkit-scrollbar-thumb': {
                            background: '#95C6C2',
                            borderRadius: 999,
                            border: '2px solid #EDF3F3',
                        },

                        '*::-webkit-scrollbar-thumb:hover': {
                            background: '#E7A699',
                        },

                        '::selection': {
                            background: 'rgba(231,166,153,.45)',
                            color: '#334547',
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
// src/components/Button.tsx
import {Button as MuiButton, CircularProgress} from '@mui/material';
import type {ButtonProps as MuiButtonProps} from '@mui/material';
import type {ReactNode} from 'react';

type ButtonProps = MuiButtonProps & {
    loading?: boolean;
    startIcon?: ReactNode;
    endIcon?: ReactNode;
};

export function Button({loading, disabled, startIcon, endIcon, children, sx, ...props}: ButtonProps) {
    return (
        <MuiButton
            {...props}
            disabled={disabled || loading}
            startIcon={loading ? undefined : startIcon}
            endIcon={loading ? undefined : endIcon}
            sx={{
                position: 'relative',
                minWidth: 88,
                gap: '6px',
                '& .MuiButton-startIcon, & .MuiButton-endIcon': {
                    margin: 0,
                    '& svg': {fontSize: '1.1rem'},
                },
                '&:hover': {
                    opacity: 1,
                    ...(props.color === 'error'
                        ? props.variant === 'outlined'
                            ? {
                                  backgroundColor: 'rgba(239, 68, 68, 0.08)',
                                  borderColor: '#EF4444',
                              }
                            : {backgroundColor: '#b91c1c'}
                        : props.variant === 'outlined'
                          ? {backgroundColor: 'rgba(0, 120, 103, 0.08)'}
                          : {backgroundColor: '#007867'}),
                },
                ...sx,
            }}
        >
            {loading && (
                <CircularProgress
                    size={16}
                    color="inherit"
                    sx={{position: 'absolute', left: '50%', transform: 'translateX(-50%)'}}
                />
            )}
            <span style={{visibility: loading ? 'hidden' : 'visible'}}>{children}</span>
        </MuiButton>
    );
}

// src/components/Button.tsx
import { Button as MuiButton, CircularProgress } from '@mui/material';
import type { ButtonProps as MuiButtonProps } from '@mui/material';
import type { ReactNode } from 'react';

type ButtonProps = MuiButtonProps & {
  loading?: boolean;
  startIcon?: ReactNode;
  endIcon?: ReactNode;
};

export function Button({
  loading,
  disabled,
  startIcon,
  endIcon,
  children,
  sx,
  variant = 'contained',
  ...props
}: ButtonProps) {
  return (
    <MuiButton
      {...props}
      variant={variant}
      disabled={disabled || loading}
      startIcon={loading ? undefined : startIcon}
      endIcon={loading ? undefined : endIcon}
      sx={{
        position: 'relative',
        minWidth: 88,
        gap: '6px',
        fontWeight: 800,
        letterSpacing: '-0.01em',
        transition:
          'transform .15s ease, box-shadow .2s ease, background-color .2s ease, border-color .2s ease',
        '& .MuiButton-startIcon, & .MuiButton-endIcon': {
          margin: 0,
          '& svg': { fontSize: '1.15rem' },
        },
        ...(variant === 'contained'
          ? {
              '&:hover': { transform: 'translateY(-1px)' },
              '&:active': { transform: 'translateY(0)' },
            }
          : {}),
        ...(variant === 'outlined'
          ? {
              borderWidth: 1.5,
              bgcolor: (t) =>
                t.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.72)',
              '&:hover': {
                borderWidth: 1.5,
                bgcolor: 'action.hover',
                transform: 'translateY(-1px)',
              },
            }
          : {}),
        '&.Mui-disabled': {
          transform: 'none',
          boxShadow: 'none',
        },
        ...sx,
      }}
    >
      {loading && (
        <CircularProgress
          size={16}
          color="inherit"
          sx={{ position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}
        />
      )}
      <span style={{ visibility: loading ? 'hidden' : 'visible' }}>{children}</span>
    </MuiButton>
  );
}

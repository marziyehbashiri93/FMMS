import { TextField } from '@mui/material';
import type { TextFieldProps } from '@mui/material';

export type RtlTextFieldProps = TextFieldProps & {
  inputDir?: 'rtl' | 'ltr';
};

export function RtlTextField({
  inputDir = 'rtl',
  inputProps,
  InputLabelProps,
  sx,
  ...props
}: RtlTextFieldProps) {
  return (
    <TextField
      {...props}
      variant={props.variant ?? 'outlined'}
      dir="rtl"
      inputProps={{
        ...inputProps,
        dir: inputDir,
        style: {
          textAlign: inputDir === 'ltr' ? 'left' : 'right',
          ...(inputProps?.style ?? {}),
        },
      }}
      InputLabelProps={{
        ...InputLabelProps,
        sx: {
          right: 28,
          left: 'auto',
          transformOrigin: 'top right',
          textAlign: 'right',
          '&.MuiInputLabel-shrink': {
            transformOrigin: 'top right',
          },
          ...(InputLabelProps?.sx ?? {}),
        },
      }}
      sx={{
        direction: 'rtl',
        '& .MuiOutlinedInput-root': {
          direction: 'rtl',
          paddingRight: '14px',
          bgcolor: 'background.paper',
          transition: 'box-shadow .18s ease, background-color .15s ease',
          '&:hover': {
            bgcolor: 'action.hover',
          },
          '&.Mui-focused': {
            bgcolor: 'background.paper',
            boxShadow: (t) =>
              t.palette.mode === 'dark'
                ? '0 0 0 3px rgba(46, 173, 116, 0.22)'
                : '0 0 0 3px rgba(15, 107, 76, 0.14)',
          },
        },
        '& .MuiOutlinedInput-notchedOutline': {
          textAlign: 'right',
          borderColor: 'divider',
        },
        '& .MuiOutlinedInput-notchedOutline legend': {
          textAlign: 'right',
        },
        '& .MuiInputAdornment-root': {
          color: 'text.secondary',
        },
        '& .MuiInputAdornment-positionStart': {
          marginLeft: 1,
          marginRight: 0,
        },
        '& .MuiInputAdornment-positionEnd': {
          marginRight: 1,
          marginLeft: 0,
        },
        ...sx,
      }}
    />
  );
}

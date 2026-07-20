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
          right: 14,
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
        },
        '& .MuiOutlinedInput-notchedOutline': {
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
        '& legend': {
          textAlign: 'right',
        },
        ...sx,
      }}
    />
  );
}

import { FormControl, InputLabel, Select } from '@mui/material';
import type { SelectProps } from '@mui/material';
import { KeyboardArrowDown } from '@mui/icons-material';
import { useId, type ReactNode } from 'react';

type RtlSelectFieldProps<T> = Omit<SelectProps<T>, 'labelId'> & {
  label: string;
  children: ReactNode;
};

export function RtlSelectField<T>({
  label,
  children,
  sx,
  ...props
}: RtlSelectFieldProps<T>) {
  const labelId = useId();

  return (
    <FormControl sx={{ minWidth: { xs: '100%', md: 220 }, direction: 'rtl', ...sx }}>
      <InputLabel id={labelId}>{label}</InputLabel>
      <Select
        {...props}
        labelId={labelId}
        label={label}
        IconComponent={KeyboardArrowDown}
        sx={{
          direction: 'rtl',
          textAlign: 'right',
          '& .MuiSelect-select': {
            pr: 4.5,
            pl: 1.75,
            textAlign: 'right',
          },
          '& .MuiSelect-icon': {
            right: 12,
            left: 'auto',
          },
        }}
      >
        {children}
      </Select>
    </FormControl>
  );
}

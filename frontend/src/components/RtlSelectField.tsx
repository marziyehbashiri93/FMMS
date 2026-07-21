import { FormControl, InputLabel, Select } from '@mui/material';
import type { SelectProps } from '@mui/material';
import { ArrowDropDown } from '@mui/icons-material';
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
        IconComponent={ArrowDropDown}
        sx={{
          direction: 'rtl',
          textAlign: 'right',
          '& .MuiSelect-select': {
            pl: 1.75,
            pr: 4.5,
            textAlign: 'right',
          },
          '& .MuiSelect-icon': {
            left: 12,
            right: 'auto',
            fontSize: 28,
          },
        }}
      >
        {children}
      </Select>
    </FormControl>
  );
}

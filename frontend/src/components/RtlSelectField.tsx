import {FormControl, InputLabel, Select} from '@mui/material';
import type {SelectProps} from '@mui/material';
import {ArrowDropDownRounded} from '@mui/icons-material';
import {useId, type ReactNode} from 'react';

type RtlSelectFieldProps<T> = Omit<SelectProps<T>, 'labelId'> & {
    label: string;
    children: ReactNode;
};

export function RtlSelectField<T>({
                                      label,
                                      children,
                                      sx,
                                      fullWidth = true,
                                      size = 'small',
                                      displayEmpty = false,
                                      value,
                                      ...props
                                  }: RtlSelectFieldProps<T>) {
    const labelId = useId();
    const hasValue = value !== undefined && value !== null && value !== '';
    const shrinkLabel = displayEmpty || hasValue;

    return (
        <FormControl
            fullWidth={fullWidth}
            size={size}
            sx={{
                direction: 'rtl',
                '& .MuiInputLabel-root': {
                    right: 28,
                    left: 'auto',
                    transformOrigin: 'right',
                },
                '& .MuiInputLabel-shrink': {
                    transformOrigin: 'right',
                },
                '& .MuiOutlinedInput-notchedOutline legend': {
                    textAlign: 'right',
                },
                ...sx,
            }}
        >
            <InputLabel id={labelId} shrink={shrinkLabel}>{label}</InputLabel>

            <Select
                {...props}
                value={value}
                displayEmpty={displayEmpty}
                size={size}
                labelId={labelId}
                label={label}
                notched={shrinkLabel}
                IconComponent={ArrowDropDownRounded}
                MenuProps={{
                    ...props.MenuProps,
                    disableScrollLock: true,
                    PaperProps: {
                        ...props.MenuProps?.PaperProps,
                        sx: {direction: 'rtl', ...(props.MenuProps?.PaperProps as {sx?: object} | undefined)?.sx},
                    },
                }}
                sx={{
                    direction: 'rtl',
                    '& .MuiSelect-select': {
                        paddingRight: '12px !important',
                        paddingLeft: '42px !important',
                        textAlign: 'right',
                    },
                    '& .MuiSelect-icon': {
                        left: 10,
                        right: 'auto',
                        fontSize: 26,
                        color: 'text.secondary',
                    },
                }}
            >
                {children}
            </Select>
        </FormControl>
    );
}

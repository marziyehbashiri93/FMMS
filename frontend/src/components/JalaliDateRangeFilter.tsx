import { Stack } from '@mui/material';
import type { SxProps, Theme } from '@mui/material/styles';
import { DATE_RANGE_ORDER_ERROR, isValidIsoDateRange } from '../utils/dateRange';
import { ClearFiltersButton } from './ClearFiltersButton';
import { JalaliDateField } from './JalaliDateField';

export type JalaliDateRangeValue = {
  fromDate: string;
  toDate: string;
};

export type JalaliDateRangeFilterProps = {
  fromDate: string;
  toDate: string;
  onChange: (next: JalaliDateRangeValue) => void;
  disabled?: boolean;
  /** When true, shows clear button that resets both dates. */
  showClear?: boolean;
  onClear?: () => void;
  clearDisabled?: boolean;
  fromLabel?: string;
  toLabel?: string;
  fieldSx?: SxProps<Theme>;
  sx?: SxProps<Theme>;
};

/**
 * Shared from/to Jalali date filter with range order validation.
 */
export function JalaliDateRangeFilter({
  fromDate,
  toDate,
  onChange,
  disabled = false,
  showClear = true,
  onClear,
  clearDisabled,
  fromLabel = 'از تاریخ',
  toLabel = 'تا تاریخ',
  fieldSx,
  sx,
}: JalaliDateRangeFilterProps) {
  const rangeValid = isValidIsoDateRange(fromDate, toDate);
  const defaultFieldSx: SxProps<Theme> = {
    width: { xs: '100%', sm: 180 },
    flexShrink: 0,
    ...((fieldSx as object) ?? {}),
  };

  return (
    <Stack
      direction={{ xs: 'column', sm: 'row' }}
      useFlexGap
      alignItems={{ xs: 'stretch', sm: 'center' }}
      sx={{ gap: 2, '& > *': { margin: 0 }, ...((sx as object) ?? {}) }}
    >
      <JalaliDateField
        label={fromLabel}
        value={fromDate}
        disabled={disabled}
        maxDate={toDate || undefined}
        error={!rangeValid}
        onChange={(next) => onChange({ fromDate: next, toDate })}
        sx={defaultFieldSx}
      />
      <JalaliDateField
        label={toLabel}
        value={toDate}
        disabled={disabled}
        minDate={fromDate || undefined}
        error={!rangeValid}
        helperText={rangeValid ? undefined : DATE_RANGE_ORDER_ERROR}
        onChange={(next) => onChange({ fromDate, toDate: next })}
        sx={defaultFieldSx}
      />
      {showClear ? (
        <ClearFiltersButton
          disabled={clearDisabled ?? ((!fromDate && !toDate) || disabled)}
          onClick={() => {
            if (onClear) {
              onClear();
              return;
            }
            onChange({ fromDate: '', toDate: '' });
          }}
        />
      ) : null}
    </Stack>
  );
}

export { isValidIsoDateRange } from '../utils/dateRange';

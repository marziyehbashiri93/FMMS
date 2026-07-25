import { useEffect, useMemo, useState } from 'react';
import {
  Autocomplete,
  Box,
  Chip,
  Stack,
  Typography,
  createFilterOptions,
} from '@mui/material';
import { AddCircleOutline, Search } from '@mui/icons-material';
import { api } from '../api/client';
import type { CentralStockItem } from '../types/fmms';
import { toFaNumber } from '../utils/format';
import { Button } from './Button';
import { RtlTextField } from './RtlTextField';

export type MaterialPickValue = {
  materialNumber: string;
  fromCatalog: boolean;
  materialName: string;
  availableQuantity: string;
};

export const EMPTY_MATERIAL_PICK: MaterialPickValue = {
  materialNumber: '',
  fromCatalog: false,
  materialName: '',
  availableQuantity: '',
};

type MaterialOption = {
  id: string;
  materialNumber: string;
  materialCode: string;
  materialName: string;
  quantity: string;
  stockTypeText: string;
  isNew?: boolean;
};

const filterMaterialOptions = createFilterOptions<MaterialOption>({
  stringify: (option) =>
    `${option.materialNumber} ${option.materialCode} ${option.materialName} ${option.stockTypeText}`,
});

function normalizePaginated<T>(payload: { results?: T[] } | T[]): T[] {
  if (Array.isArray(payload)) return payload;
  return payload.results ?? [];
}

function toOption(item: CentralStockItem): MaterialOption {
  const code = item.material_code || item.material.replace(/^0+/, '') || item.material;
  const qty = String(item.quantity ?? '0').trim();
  return {
    id: item.id,
    materialNumber: code,
    materialCode: code,
    materialName: (item.material_name || '').trim(),
    quantity: qty,
    stockTypeText: item.inventory_stock_type_text || '',
  };
}

function pickOutsideCatalog(code: string, name = ''): MaterialPickValue {
  return {
    materialNumber: code.trim(),
    fromCatalog: false,
    materialName: name.trim(),
    availableQuantity: '0',
  };
}

/**
 * Searchable warehouse material dropdown; out-of-catalog codes select in-place.
 */
export function MaterialStockPicker({
  label = 'انتخاب قطعه از انبار مرکزی',
  value,
  onChange,
  disabled = false,
  size = 'small',
}: {
  label?: string;
  value: MaterialPickValue;
  onChange: (next: MaterialPickValue) => void;
  disabled?: boolean;
  size?: 'small' | 'medium';
}) {
  const [options, setOptions] = useState<MaterialOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [inputValue, setInputValue] = useState('');

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError('');
    void api
      .listCentralStock({ storageLocation: 'KH08', page: 1, pageSize: 500 })
      .then((payload) => {
        if (!active) return;
        const rows = normalizePaginated(payload).map(toOption);
        const seen = new Set<string>();
        const unique = rows.filter((row) => {
          if (seen.has(row.materialNumber)) return false;
          seen.add(row.materialNumber);
          return true;
        });
        unique.sort((a, b) => a.materialNumber.localeCompare(b.materialNumber, 'en'));
        setOptions(unique);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setLoadError(err instanceof Error ? err.message : 'بارگذاری لیست قطعات ناموفق بود');
        setOptions([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!value.materialNumber) {
      setInputValue('');
      return;
    }
    if (!value.fromCatalog) {
      setInputValue(value.materialNumber);
    }
  }, [value.materialNumber, value.fromCatalog]);

  const selected = useMemo(() => {
    if (!value.materialNumber || !value.fromCatalog) return null;
    return options.find((item) => item.materialNumber === value.materialNumber) ?? null;
  }, [options, value.materialNumber, value.fromCatalog]);

  const applyOutsideCatalog = (rawCode: string) => {
    const code = rawCode.trim();
    if (!code) return;
    onChange(pickOutsideCatalog(code));
    setInputValue(code);
  };

  const helperText = (() => {
    if (loadError) return loadError;
    if (value.materialNumber && !value.fromCatalog) {
      return `خارج از انبار: ${value.materialNumber} — ترابری فقط خرید از بیرون خواهد داشت`;
    }
    if (selected) {
      return selected.materialName
        ? `${selected.materialName} · موجودی ${toFaNumber(selected.quantity)}`
        : `انتخاب‌شده از انبار · موجودی ${toFaNumber(selected.quantity)}`;
    }
    return `${toFaNumber(options.length)} قطعه در لیست انبار مرکزی`;
  })();

  return (
    <Stack spacing={1} sx={{ minWidth: { xs: '100%', sm: 280 }, flex: 1 }}>
      <Autocomplete
        openOnFocus
        autoHighlight
        clearOnBlur={false}
        disabled={disabled}
        loading={loading}
        options={options}
        value={selected}
        inputValue={inputValue}
        onInputChange={(_event, next, reason) => {
          if (reason === 'reset') return;
          setInputValue(next);
          if (value.materialNumber && !value.fromCatalog && next !== value.materialNumber) {
            onChange(EMPTY_MATERIAL_PICK);
          }
        }}
        onChange={(_event, next) => {
          if (!next) {
            onChange(EMPTY_MATERIAL_PICK);
            setInputValue('');
            return;
          }
          if (next.isNew) {
            applyOutsideCatalog(next.materialNumber);
            return;
          }
          onChange({
            materialNumber: next.materialNumber,
            fromCatalog: true,
            materialName: next.materialName,
            availableQuantity: next.quantity || '0',
          });
          setInputValue('');
        }}
        getOptionLabel={(option) =>
          option.materialName
            ? `${option.materialNumber} — ${option.materialName}`
            : option.materialNumber
        }
        isOptionEqualToValue={(option, current) =>
          option.materialNumber === current.materialNumber
        }
        filterOptions={(items, params) => {
          const filtered = filterMaterialOptions(items, params).slice(0, 60);
          const query = params.inputValue.trim();
          if (!query) return filtered;

          const exists = items.some(
            (item) =>
              item.materialNumber.toLowerCase() === query.toLowerCase() ||
              item.materialCode.toLowerCase() === query.toLowerCase(),
          );
          if (!exists) {
            filtered.push({
              id: `new-${query}`,
              materialNumber: query,
              materialCode: query,
              materialName: '',
              quantity: '',
              stockTypeText: '',
              isNew: true,
            });
          }
          return filtered;
        }}
        noOptionsText={
          options.length === 0
            ? 'لیست انبار خالی است — کد را تایپ کنید یا افزودن دستی را بزنید'
            : 'موردی یافت نشد — می‌توانید قطعه را خارج از انبار اضافه کنید'
        }
        loadingText="در حال بارگذاری لیست انبار..."
        renderOption={(props, option) => {
          const { key, ...rest } = props;
          if (option.isNew) {
            return (
              <Box
                component="li"
                key={key}
                {...rest}
                dir="rtl"
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  color: 'primary.main',
                  fontWeight: 700,
                }}
              >
                <AddCircleOutline fontSize="small" />
                افزودن «{option.materialNumber}» خارج از انبار
              </Box>
            );
          }
          return (
            <Box
              component="li"
              key={key}
              {...rest}
              dir="rtl"
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 1.5,
                width: '100%',
              }}
            >
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography fontWeight={800} noWrap>
                  {option.materialNumber}
                </Typography>
                {option.materialName ? (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    noWrap
                    sx={{ fontWeight: 600 }}
                  >
                    {option.materialName}
                  </Typography>
                ) : null}
              </Box>
              <Chip
                size="small"
                color="success"
                variant="filled"
                label={`موجودی ${toFaNumber(option.quantity || '0')}`}
                sx={{
                  fontWeight: 800,
                  flexShrink: 0,
                  '& .MuiChip-label': { px: 1 },
                }}
              />
            </Box>
          );
        }}
        renderInput={(params) => (
          <RtlTextField
            {...params}
            label={label}
            size={size}
            placeholder="جستجو در لیست قطعات انبار..."
            helperText={helperText}
            error={Boolean(loadError)}
            InputProps={{
              ...params.InputProps,
              startAdornment: (
                <>
                  <Search fontSize="small" color="action" sx={{ ml: 0.5 }} />
                  {params.InputProps.startAdornment}
                </>
              ),
            }}
          />
        )}
      />

      {selected ? (
        <Chip
          size="small"
          color="success"
          variant="outlined"
          label={
            selected.materialName
              ? `${selected.materialNumber} · ${selected.materialName} · موجودی ${toFaNumber(selected.quantity)}`
              : `${selected.materialNumber} · موجودی ${toFaNumber(selected.quantity)}`
          }
          onDelete={disabled ? undefined : () => onChange(EMPTY_MATERIAL_PICK)}
          sx={{ alignSelf: 'flex-start', maxWidth: '100%' }}
        />
      ) : null}

      {value.materialNumber && !value.fromCatalog ? (
        <Chip
          size="small"
          color="warning"
          variant="outlined"
          label={`خارج از انبار: ${value.materialNumber}`}
          onDelete={disabled ? undefined : () => onChange(EMPTY_MATERIAL_PICK)}
          sx={{ alignSelf: 'flex-start', maxWidth: '100%' }}
        />
      ) : null}

      <Button
        size="small"
        variant="text"
        startIcon={<AddCircleOutline />}
        disabled={disabled || !inputValue.trim()}
        onClick={() => applyOutsideCatalog(inputValue)}
        sx={{ alignSelf: 'flex-start' }}
      >
        قطعه در لیست نیست؟ افزودن خارج از انبار
      </Button>
    </Stack>
  );
}

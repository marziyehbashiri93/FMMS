import { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, MenuItem, Stack, Typography, useMediaQuery } from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { Search } from '@mui/icons-material';
import { Inventory2 } from '../../components/icons3d/Icons3D';
import { api } from '../../api/client';
import { Button } from '../../components/Button';
import { ClearFiltersButton } from '../../components/ClearFiltersButton';
import { FeaturePage } from '../../components/FeaturePage';
import { FilterPanel } from '../../components/FilterPanel';
import { PageHeader } from '../../components/PageHeader';
import { ErrorState } from '../../components/States';
import { PlainStatusBadge } from '../../components/StatusBadge';
import { RtlDataTable, type RtlDataTableColumn } from '../../components/RtlDataTable';
import { RtlPagination } from '../../components/RtlPagination';
import { RtlSelectField } from '../../components/RtlSelectField';
import { RtlTextField } from '../../components/RtlTextField';
import type { CentralStockItem, Paginated } from '../../types/fmms';
import { toFaNumber } from '../../utils/format';

const PAGE_SIZE = 50;

const DEFAULT_STORAGE_LOCATIONS = [
  { value: '', label: 'همه انبارها' },
  { value: 'KH08', label: 'KH08 — انبار مرکزی قطعات یدکی' },
];

function normalizeStock(payload: CentralStockItem[] | Paginated<CentralStockItem>) {
  if (Array.isArray(payload)) {
    return { rows: payload, count: payload.length };
  }
  return { rows: payload.results ?? [], count: payload.count ?? 0 };
}

function formatDecimal(value: string | number): string {
  const numeric = Number(value ?? 0);
  if (!Number.isFinite(numeric)) return toFaNumber(String(value ?? '0'));
  return toFaNumber(numeric.toLocaleString('en-US', { maximumFractionDigits: 3 }));
}

function formatMoney(value: string | number, currency: string): string {
  const numeric = Number(value ?? 0);
  const amount = Number.isFinite(numeric)
    ? numeric.toLocaleString('en-US', { maximumFractionDigits: 2 })
    : String(value ?? '0');
  return `${toFaNumber(amount)} ${currency || ''}`.trim();
}

/**
 * SAP central stock browser for materials and warehouse inventory.
 */
export function MaterialsPage() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const [rows, setRows] = useState<CentralStockItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [plant, setPlant] = useState('');
  const [storageLocation, setStorageLocation] = useState('');
  const [page, setPage] = useState(1);
  const [count, setCount] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await api.listCentralStock({
        plant: plant.trim() || undefined,
        storageLocation: storageLocation || undefined,
        search: search.trim() || undefined,
        page,
        pageSize: PAGE_SIZE,
      });
      const normalized = normalizeStock(payload);
      setRows(normalized.rows);
      setCount(normalized.count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت موجودی SAP انجام نشد');
    } finally {
      setLoading(false);
    }
  }, [page, plant, search, storageLocation]);

  useEffect(() => {
    void load();
  }, [load]);

  const columns = useMemo<Array<RtlDataTableColumn<CentralStockItem, string>>>(
    () => [
      {
        key: 'material',
        label: 'کد متریال SAP',
        minWidth: 150,
        render: (row) => (
          <Stack spacing={0.25}>
            <Typography fontWeight={900}>{row.material}</Typography>
            <Typography variant="caption" color="text.secondary">
              {row.material_code || '—'}
            </Typography>
          </Stack>
        ),
      },
      {
        key: 'material_name',
        label: 'نام قطعه',
        minWidth: 220,
        render: (row) => row.material_name || '—',
      },
      {
        key: 'quantity',
        label: 'موجودی',
        minWidth: 120,
        render: (row) => (
          <Typography fontWeight={900}>
            {formatDecimal(row.quantity)} {row.base_unit}
          </Typography>
        ),
      },
      {
        key: 'warehouse',
        label: 'انبار',
        minWidth: 140,
        render: (row) => `${row.plant || '—'} / ${row.storage_location || '—'}`,
      },
      {
        key: 'stock_type',
        label: 'نوع موجودی',
        minWidth: 150,
        render: (row) =>
          row.inventory_stock_type_text || row.inventory_stock_type || '—',
      },
      {
        key: 'stock_value',
        label: 'ارزش موجودی',
        minWidth: 140,
        render: (row) => formatMoney(row.stock_value, row.display_currency),
      },
      {
        key: 'status',
        label: 'وضعیت',
        minWidth: 100,
        render: (row) => (
          <PlainStatusBadge
            label={row.is_active ? 'فعال' : 'غیرفعال'}
            tone={row.is_active ? 'success' : 'neutral'}
          />
        ),
      },
    ],
    [],
  );

  const applyFilters = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const resetFilters = () => {
    setSearchInput('');
    setSearch('');
    setPlant('');
    setStorageLocation('');
    setPage(1);
  };

  const hasFilters = Boolean(search || searchInput || plant || storageLocation);
  const pageCount = Math.max(1, Math.ceil(count / PAGE_SIZE));

  return (
    <FeaturePage>
      <PageHeader
        title="قطعات و انبار"
        description="لیست قطعات موجود در انبار SAP"
        breadcrumbs={[{ label: 'مدیریت' }, { label: 'قطعات و انبار' }]}
      />

      <FilterPanel>
        <RtlTextField
          label="جستجو در کد یا نام قطعه"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          size="small"
          onKeyDown={(event) => {
            if (event.key === 'Enter') applyFilters();
          }}
        />
        <RtlTextField
          label="Plant"
          value={plant}
          onChange={(event) => setPlant(event.target.value)}
          size="small"
        />
        <RtlSelectField
          label="محل انبار"
          value={storageLocation}
          onChange={(event) => setStorageLocation(event.target.value)}
          size="small"
        >
          {DEFAULT_STORAGE_LOCATIONS.map((item) => (
            <MenuItem key={item.value || 'all'} value={item.value}>
              {item.label}
            </MenuItem>
          ))}
        </RtlSelectField>
        <Button
          variant="contained"
          startIcon={<Search />}
          onClick={applyFilters}
          sx={{ height: 40, minHeight: 40 }}
        >
          اعمال
        </Button>
        <ClearFiltersButton onClick={resetFilters} disabled={!hasFilters} />
      </FilterPanel>

      {!error && rows.length > 0 ? (
        <Alert severity="info">
          این لیست از snapshot موجودی SAP خوانده می‌شود و تغییر مستقیم در موجودی از این صفحه انجام نمی‌شود.
        </Alert>
      ) : null}

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {!error ? (
        <RtlDataTable
          columns={columns}
          rows={rows}
          getRowKey={(row) => row.id}
          loading={loading}
          emptyMessage="موجودی SAP یافت نشد"
          emptySubtitle="پس از sync موجودی انبار مرکزی از SAP، اقلام اینجا نمایش داده می‌شوند."
          emptyIcon={Inventory2}
          minWidth={isMobile ? 760 : 980}
        />
      ) : null}

      {!error ? (
        <RtlPagination
          page={page}
          count={pageCount}
          onChange={setPage}
          totalItems={count}
          pageSize={PAGE_SIZE}
          disabled={loading}
        />
      ) : null}
    </FeaturePage>
  );
}

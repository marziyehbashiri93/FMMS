import {
  Box, Paper, Skeleton, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TableSortLabel, Typography,
} from '@mui/material';
import { useState, type ReactNode } from 'react';

export type RtlDataTableColumn<T, K extends string = string> = {
  key: K;
  label: string;
  align?: 'right' | 'left' | 'center';
  minWidth?: number;
  sortable?: boolean;
  render?: (row: T) => ReactNode;
};

type Props<T, K extends string = string> = {
  columns: Array<RtlDataTableColumn<T, K>>;
  rows: T[];
  getRowKey?: (row: T) => string;
  minWidth?: number;
  orderBy?: K;
  order?: 'asc' | 'desc';
  onSort?: (key: K) => void;
  loading?: boolean;
  skeletonRows?: number;
  emptyMessage?: string;
};

export type Column<T, K extends string = string> = RtlDataTableColumn<T, K>;

export function RtlDataTable<T, K extends string = string>({
  columns,
  rows,
  getRowKey,
  minWidth = 720,
  orderBy,
  order = 'asc',
  onSort,
  loading = false,
  skeletonRows = 5,
  emptyMessage = 'داده‌ای یافت نشد',
}: Props<T, K>) {
  const [internalOrderBy, setInternalOrderBy] = useState<K | ''>('');
  const [internalOrder, setInternalOrder] = useState<'asc' | 'desc'>('asc');
  const activeOrderBy = orderBy ?? internalOrderBy;
  const activeOrder = orderBy ? order : internalOrder;

  const handleSort = (key: K) => {
    if (onSort) {
      onSort(key);
      return;
    }
    setInternalOrder(internalOrderBy === key && internalOrder === 'asc' ? 'desc' : 'asc');
    setInternalOrderBy(key);
  };

  const rowKey = (row: T, index: number) => {
    if (getRowKey) return getRowKey(row);
    const candidate = (row as { id?: string | number }).id;
    return candidate === undefined ? String(index) : String(candidate);
  };

  return (
    <Paper>
      <TableContainer sx={{ overflowX: 'auto' }}>
        <Table dir="rtl" sx={{ minWidth }}>
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell
                  key={col.key}
                  align={col.align ?? 'right'}
                  sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}
                >
                  {col.sortable ? (
                    <TableSortLabel
                      active={activeOrderBy === col.key}
                      direction={activeOrderBy === col.key ? activeOrder : 'asc'}
                      onClick={() => handleSort(col.key)}
                      sx={{ flexDirection: 'row-reverse', gap: 0.5 }}
                    >
                      {col.label}
                    </TableSortLabel>
                  ) : col.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              Array.from({ length: skeletonRows }).map((_, i) => (
                <TableRow key={i}>
                  {columns.map((col) => (
                    <TableCell key={col.key} align={col.align ?? 'right'} sx={{ minWidth: col.minWidth }}>
                      <Skeleton variant="text" width="80%" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length}>
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography color="text.secondary">{emptyMessage}</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row, index) => (
                <TableRow key={rowKey(row, index)} hover>
                  {columns.map((col) => (
                    <TableCell key={col.key} align={col.align ?? 'right'} sx={{ minWidth: col.minWidth }}>
                      {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Paper>
  );
}

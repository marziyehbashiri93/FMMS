import {
  Paper, Skeleton, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TableSortLabel,
} from '@mui/material';
import { Inbox } from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';
import { useState, type ReactNode } from 'react';
import { EmptyState } from './States';

export type RtlDataTableSkeleton = 'text' | 'badge' | 'button';

export type RtlDataTableColumn<T, K extends string = string> = {
  key: K;
  label: string;
  align?: 'right' | 'left' | 'center';
  minWidth?: number;
  sortable?: boolean;
  skeleton?: RtlDataTableSkeleton;
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
  emptySubtitle?: string;
  emptyIcon?: SvgIconComponent;
  /**
   * When true, hide the table chrome on empty data and show only EmptyState.
   * Use in detail modals; keep false on list pages so headers remain visible.
   */
  standaloneEmpty?: boolean;
};

export type Column<T, K extends string = string> = RtlDataTableColumn<T, K>;

const TEXT_WIDTHS = ['72%', '88%', '64%', '80%', '56%', '70%'];

function resolveSkeleton(column: RtlDataTableColumn<unknown, string>): RtlDataTableSkeleton {
  if (column.skeleton) return column.skeleton;
  if (column.key === 'status' || column.key.includes('status')) return 'badge';
  if (column.key === 'actions' || column.align === 'center') return 'button';
  return 'text';
}

function SkeletonCell({
  column,
  columnIndex,
}: {
  column: RtlDataTableColumn<unknown, string>;
  columnIndex: number;
}) {
  const variant = resolveSkeleton(column);
  const align = column.align ?? 'right';

  if (variant === 'badge') {
    return (
      <Skeleton
        variant="rounded"
        width={96}
        height={28}
        animation="wave"
        sx={{
          borderRadius: (t) => t.radius('lg'),
          ...(align === 'center' ? { mx: 'auto' } : align === 'left' ? { mr: 'auto' } : { ml: 'auto' }),
        }}
      />
    );
  }

  if (variant === 'button') {
    return (
      <Skeleton
        variant="rounded"
        width={76}
        height={32}
        animation="wave"
        sx={{ borderRadius: (t) => t.radius('md'), mx: 'auto' }}
      />
    );
  }

  return (
    <Skeleton
      variant="rounded"
      width={TEXT_WIDTHS[columnIndex % TEXT_WIDTHS.length]}
      height={16}
      animation="wave"
      sx={{
        borderRadius: (t) => t.radius('sm'),
        ...(align === 'center' ? { mx: 'auto' } : align === 'left' ? { mr: 'auto' } : { ml: 'auto' }),
      }}
    />
  );
}

export function RtlDataTable<T, K extends string = string>({
  columns,
  rows,
  getRowKey,
  minWidth = 720,
  orderBy,
  order = 'asc',
  onSort,
  loading = false,
  skeletonRows = 6,
  emptyMessage = 'داده‌ای یافت نشد',
  emptySubtitle,
  emptyIcon = Inbox,
  standaloneEmpty = false,
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

  if (standaloneEmpty && !loading && rows.length === 0) {
    return (
      <EmptyState
        title={emptyMessage}
        subtitle={emptySubtitle}
        icon={emptyIcon}
      />
    );
  }

  // Keep existing rows while refetching (e.g. sort) so column widths / header stay stable.
  const showSkeleton = loading && rows.length === 0;

  return (
    <Paper
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: (t) => t.radius('md'),
        overflow: 'hidden',
      }}
    >
      <TableContainer sx={{ overflowX: 'auto' }}>
        <Table dir="rtl" sx={{ minWidth, opacity: loading && !showSkeleton ? 0.72 : 1 }}>
          <TableHead>
            <TableRow>
              {columns.map((col) => (
                <TableCell
                  key={col.key}
                  align={col.align ?? 'right'}
                  sx={{ fontWeight: 700, whiteSpace: 'nowrap', minWidth: col.minWidth }}
                >
                  {col.sortable ? (
                    <TableSortLabel
                      active={activeOrderBy === col.key}
                      direction={activeOrderBy === col.key ? activeOrder : 'asc'}
                      disabled={loading}
                      onClick={() => handleSort(col.key)}
                      sx={{ flexDirection: 'row-reverse', gap: 0.5 }}
                    >
                      {col.label}
                    </TableSortLabel>
                  ) : (
                    col.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {showSkeleton ? (
              Array.from({ length: skeletonRows }).map((_, rowIndex) => (
                <TableRow key={`skeleton-${rowIndex}`}>
                  {columns.map((col, columnIndex) => (
                    <TableCell
                      key={col.key}
                      align={col.align ?? 'right'}
                      sx={{ minWidth: col.minWidth, py: 1.75 }}
                    >
                      <SkeletonCell
                        column={col as RtlDataTableColumn<unknown, string>}
                        columnIndex={columnIndex + rowIndex}
                      />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  sx={{
                    borderBottom: 'none',
                    py: 0,
                    '&:hover': { backgroundColor: 'transparent' },
                  }}
                >
                  <EmptyState
                    title={emptyMessage}
                    subtitle={emptySubtitle}
                    icon={emptyIcon}
                    boxed={false}
                  />
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

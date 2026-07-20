import {
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
} from '@mui/material';
import type { ReactNode } from 'react';



import { useTheme } from "@mui/material/styles";








export interface RtlDataTableColumn<T, K extends string> {
  key: K;
  label: string;
  align?: 'right' | 'left' | 'center';
  sortable?: boolean;
  render: (row: T) => ReactNode;
}

export function RtlDataTable<T, K extends string>({

  columns,
  rows,
  getRowKey,
  minWidth = 720,
  orderBy,
  order = 'asc',
  onSort,
}: {

  columns: Array<RtlDataTableColumn<T, K>>;
  rows: T[];
  getRowKey: (row: T) => string;
  minWidth?: number;
  orderBy?: K;
  order?: 'asc' | 'desc';
  onSort?: (key: K) => void;
}) {

    const theme = useTheme();

  console.log(theme.direction);

  return (

    <TableContainer component={Card} dir="rtl">
      <Table size="small" dir="rtl"
  sx={(theme) => ({
    minWidth,
    direction: theme.direction,
  })}
      >
        <TableHead >
          <TableRow >
            {columns.map((column) => (
              <TableCell key={column.key} align={column.align ?? 'left'} text-align
              >
                {column.sortable && onSort ? (
                  <TableSortLabel
                    active={orderBy === column.key}
                    direction={orderBy === column.key ? order : 'asc'}
                    onClick={() => onSort(column.key)}
                  >
                    {column.label}
                  </TableSortLabel>
                ) : (
                  column.label
                )}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody dir="rtl">
          {rows.map((row) => (
            <TableRow key={getRowKey(row)} hover dir="rtl">
              {columns.map((column) => (
                <TableCell key={column.key} align={column.align ?? 'right'} dir="rtl">
                  {column.render(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

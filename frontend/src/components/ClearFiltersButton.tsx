import { RestartAlt } from '@mui/icons-material';
import type { SxProps, Theme } from '@mui/material/styles';
import { Button } from './Button';

export type ClearFiltersButtonProps = {
  onClick: () => void;
  disabled?: boolean;
  label?: string;
  sx?: SxProps<Theme>;
};

/**
 * Shared outlined error button used to reset active filters.
 */
export function ClearFiltersButton({
  onClick,
  disabled = false,
  label = 'پاک کردن فیلترها',
  sx,
}: ClearFiltersButtonProps) {
  return (
    <Button
      variant="outlined"
      color="error"
      size="small"
      startIcon={<RestartAlt />}
      onClick={onClick}
      disabled={disabled}
      sx={{
        minWidth: { xs: '100%', sm: 'auto' },
        width: { xs: '100%', sm: 'auto' },
        px: 1.5,
        height: 40,
        minHeight: 40,
        flexShrink: 0,
        whiteSpace: 'nowrap',
        ...((sx as object) ?? {}),
      }}
    >
      {label}
    </Button>
  );
}

import type {PaletteColor} from '@mui/material/styles';

/**
 * Soft copper ↔ white gradient: pale at one end, richer copper at the other.
 */
export function brandHeroGradient(_primary: PaletteColor, secondary: PaletteColor): string {
  return [
    `radial-gradient(90% 70% at 80% 20%, #FFFFFFCC 0%, transparent 55%)`,
    `linear-gradient(155deg, #FFFFFF 0%, ${secondary.light} 28%, ${secondary.main} 72%, ${secondary.dark} 100%)`,
  ].join(', ');
}

/** Page-header rail: white → soft copper → bold copper. */
export function brandAccentBarGradient(_primary: PaletteColor, secondary: PaletteColor): string {
  return `linear-gradient(180deg, #FFFFFF 0%, ${secondary.light} 35%, ${secondary.main} 100%)`;
}

/** Icon chip: pale copper to saturated copper. */
export function brandIconGradient(_primary: PaletteColor, secondary: PaletteColor): string {
  return `linear-gradient(145deg, #FFFFFF 0%, ${secondary.light} 40%, ${secondary.main} 100%)`;
}

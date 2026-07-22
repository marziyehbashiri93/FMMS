export const radii = {
  /** Tiny elements — skeleton lines, dense chips */
  xs: 4,
  /** Compact controls — chips, small badges */
  sm: 6,
  /** Default surfaces — buttons, inputs, cards, table, modal */
  md: 8,
  /** Medium accents — icon wells, nav marks */
  lg: 12,
  /** Larger panels / decorative blocks */
  xl: 16,
} as const;

export type Radii = typeof radii;
export type RadiusToken = keyof Radii;

/**
 * Pixel string for MUI `sx`.
 *
 * Unitless numbers in `sx` are multiplied by `theme.shape.borderRadius`,
 * so always pass an explicit `px` value from these tokens.
 *
 * @example
 * sx={{ borderRadius: (t) => t.radius('md') }}
 */
export function radiusPx(token: RadiusToken, themeRadii: Radii = radii): string {
  return `${themeRadii[token]}px`;
}

declare module '@mui/material/styles' {
  interface Theme {
    radii: Radii;
    /** Returns e.g. `8px` — safe for `sx.borderRadius`. */
    radius: (token: RadiusToken) => string;
  }

  interface ThemeOptions {
    radii?: Radii;
  }
}

import { NO_VALUE_LABEL } from './colors'

// Distinct values of a category field, sorted, with documents lacking a value
// ("(no value)") last. Shared by the strip plot and confusion matrix so their rows
// line up.
export function categoryKeys(values: (string | null)[]): string[] {
  const keys = new Set(values.map((value) => value ?? NO_VALUE_LABEL))
  return [...keys].sort((a, b) => {
    if (a === NO_VALUE_LABEL) return 1
    if (b === NO_VALUE_LABEL) return -1
    return a.localeCompare(b)
  })
}

// A linear axis domain covering `values` with a little padding (or a unit-wide one
// around a single value), so points don't sit on the plot's edges.
export function computeDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1]
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) return [min - 1, max + 1]
  const pad = (max - min) * 0.03
  return [min - pad, max + pad]
}

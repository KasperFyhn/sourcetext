export function clamp(
  value: number,
  min: number | undefined,
  max: number | undefined,
): number {
  let v = value
  if (min !== undefined) v = Math.max(v, min)
  if (max !== undefined) v = Math.min(v, max)
  return v
}

// A step at the order of magnitude of the field's actual range (e.g. 0.01 for a
// 0-1 score, 1 for a 20-90 range, 100 for a 0-1000 range), rather than a fixed
// step of 1 across every field regardless of scale.
export function stepForRange(
  min: number | undefined,
  max: number | undefined,
): number {
  if (min === undefined || max === undefined) return 1
  const range = Math.abs(max - min)
  if (range === 0) return 1
  const exponent = Math.floor(Math.log10(range)) - 1
  return Math.pow(10, exponent)
}

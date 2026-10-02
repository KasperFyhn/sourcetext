// dataviz skill's categorical palette, slots 1-3 (blue/orange/aqua). A plot shows
// every category simultaneously, so every pair of colors must be mutually
// distinguishable ("all-pairs") rather than just neighbor-to-neighbor — only the
// first 3 of the palette's 8 slots are validated for that; a 4th color risks two
// categories reading as the same hue to color-blind viewers. Additional categories
// fold into a shared neutral "Other" bucket instead of a 4th generated hue.
const CATEGORICAL_COLORS = ['#2a78d6', '#eb6834', '#1baf7a']
const OTHER_COLOR = '#898781'
const OTHER_LABEL = 'Other'
export const NO_VALUE_LABEL = '(no value)'

export interface ColorScale {
  colorOf: (value: string | null) => string
  legend: { label: string; color: string }[]
}

// Colors the most frequent values (up to the palette's all-pairs-safe cap) and
// folds everything else — including documents with no value for the field — into
// one neutral "Other" bucket, ranked by frequency for a stable, meaningful order.
export function buildColorScale(values: (string | null)[]): ColorScale {
  const counts = new Map<string, number>()
  const order: string[] = []
  for (const value of values) {
    const key = value ?? NO_VALUE_LABEL
    if (!counts.has(key)) order.push(key)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }
  const ranked = [...order].sort(
    (a, b) => (counts.get(b) ?? 0) - (counts.get(a) ?? 0),
  )
  const top = ranked.slice(0, CATEGORICAL_COLORS.length)
  const colorByKey = new Map(
    top.map((key, index) => [key, CATEGORICAL_COLORS[index]]),
  )
  const legend = top.map((key) => ({ label: key, color: colorByKey.get(key)! }))
  if (ranked.length > top.length)
    legend.push({ label: OTHER_LABEL, color: OTHER_COLOR })
  return {
    colorOf: (value) => colorByKey.get(value ?? NO_VALUE_LABEL) ?? OTHER_COLOR,
    legend,
  }
}

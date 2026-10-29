import type { Field } from '../../api/types'
import {
  CONFIDENCE,
  GOLD_LABEL,
  GROUP,
  PREDICTION,
} from '../../lib/namedFields'

// A point_2d field plotted directly, or two fields as axes.
export type Mode = 'point2d' | 'fields'

export interface PlotSelection {
  mode: Mode
  pointField: string | null
  xField: string | null
  yField: string | null
  colorField: string | null
}

// Named fields, if present, make the most useful defaults for a strip plot
// (confidence per gold label, colored by prediction).
const DEFAULT_SCORE = CONFIDENCE
const DEFAULT_CATEGORIES = [GOLD_LABEL, PREDICTION]
const DEFAULT_COLOR = [GROUP, PREDICTION]

export const isCategorical = (field: Field | undefined) =>
  field?.type === 'label'

function pickDefault(names: string[], preferred: string[]): string | null {
  return preferred.find((name) => names.includes(name)) ?? names[0] ?? null
}

// Sensible defaults for the mode/axis/color selectors, from the plottable fields.
export function defaultPlotSelection(plotFields: Field[]): PlotSelection {
  const selection: PlotSelection = {
    mode: 'point2d',
    pointField: null,
    xField: null,
    yField: null,
    colorField: null,
  }
  const names = (type: Field['type'][]) =>
    plotFields.filter((f) => type.includes(f.type)).map((f) => f.name)
  const point2d = names(['point_2d'])
  const scores = names(['score'])
  const categories = names(['label'])

  if (point2d.length > 0) {
    selection.pointField = point2d[0]
    selection.mode = 'point2d'
  } else if (scores.length >= 2) {
    selection.xField = scores[0]
    selection.yField = scores[1]
    selection.mode = 'fields'
  } else if (scores.length === 1 && categories.length > 0) {
    const category = pickDefault(categories, DEFAULT_CATEGORIES)
    selection.xField = pickDefault(scores, [DEFAULT_SCORE])
    selection.yField = category
    selection.mode = 'fields'
    categories.splice(categories.indexOf(category!), 1)
  }
  selection.colorField = pickDefault(categories, DEFAULT_COLOR)
  return selection
}

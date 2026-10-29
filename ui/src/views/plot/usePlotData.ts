import { fetchScatter, fetchStrip } from '../../api/plot'
import type { ScatterPoint, StripPoint } from '../../api/plot'
import type { Field, Filter } from '../../api/types'
import type { LabelDefinitions } from '../../fields/label/labelDefinitions'
import { useFetch } from '../../hooks/useFetch'
import { isCategorical } from './plotDefaults'
import type { PlotSelection } from './plotDefaults'
import type { StripOrientation } from './StripPlot'

// What gets drawn: a scatterplot (point_2d field, or two score axes), or a strip
// plot (one score axis, one categorical axis — a beeswarm per category, so
// documents sharing a category don't stack on a line). Axis labels, orientation and
// label definitions are captured with the request, so they always match the points
// shown.
export type PlotData =
  | {
      kind: 'scatter'
      points: ScatterPoint[]
      xLabel: string
      yLabel: string
      colorDefinitions: LabelDefinitions
    }
  | {
      kind: 'strip'
      points: StripPoint[]
      orientation: StripOrientation
      scoreLabel: string
      categoryLabel: string
      categoryDefinitions: LabelDefinitions
      colorDefinitions: LabelDefinitions
    }

// The request for the current selection, or null if there's nothing to fetch
// (e.g. both axes categorical: the view shows a hint instead).
function plotRequest(
  { mode, pointField, xField, yField, colorField }: PlotSelection,
  plotFields: Field[],
  filters: Filter[],
): (() => Promise<PlotData>) | null {
  const definitionsOf = (name: string | null) =>
    plotFields.find((f) => f.name === name)?.definitions
  const fieldByName = (name: string | null) =>
    plotFields.find((f) => f.name === name)
  const xCategorical = isCategorical(fieldByName(xField))
  const yCategorical = isCategorical(fieldByName(yField))
  const color = colorField ? { colorField } : {}
  const colorDefinitions = definitionsOf(colorField)
  const filtersQuery = filters.length > 0 ? { filters } : {}

  if (mode === 'point2d' && pointField) {
    return () =>
      fetchScatter({ field: pointField, ...color, ...filtersQuery }).then(
        (r) => ({
          kind: 'scatter',
          points: r.points,
          xLabel: 'x',
          yLabel: 'y',
          colorDefinitions,
        }),
      )
  }
  if (mode === 'fields' && xField && yField) {
    if (!xCategorical && !yCategorical) {
      return () =>
        fetchScatter({ xField, yField, ...color, ...filtersQuery }).then(
          (r) => ({
            kind: 'scatter',
            points: r.points,
            xLabel: xField,
            yLabel: yField,
            colorDefinitions,
          }),
        )
    }
    if (xCategorical !== yCategorical) {
      const [scoreField, categoryField] = xCategorical
        ? [yField, xField]
        : [xField, yField]
      return () =>
        fetchStrip({
          xField: scoreField,
          rowField: categoryField,
          ...color,
          ...filtersQuery,
        }).then((r) => ({
          kind: 'strip',
          points: r.points,
          // Categories on the y axis are laid out as rows, on the x axis as columns.
          orientation: yCategorical ? 'horizontal' : 'vertical',
          scoreLabel: scoreField,
          categoryLabel: categoryField,
          categoryDefinitions: definitionsOf(categoryField),
          colorDefinitions,
        }))
    }
  }
  return null
}

// The points for the current selection, refetched whenever it or the filters change.
export function usePlotData(
  selection: PlotSelection,
  plotFields: Field[],
  filters: Filter[],
) {
  const { mode, pointField, xField, yField, colorField } = selection
  return useFetch(plotRequest(selection, plotFields, filters), [
    mode,
    pointField,
    xField,
    yField,
    colorField,
    filters,
    plotFields,
  ])
}

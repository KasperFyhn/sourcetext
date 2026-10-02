import {
  Alert,
  Box,
  Flex,
  Group,
  Loader,
  Select,
  Stack,
  Text,
} from '@mantine/core'
import { useEffect, useState } from 'react'

import { fetchDocument, fetchFields, fetchScatter, fetchStrip } from '../api'
import type {
  Document,
  Field,
  FieldFilter,
  ScatterPoint,
  StripPoint,
} from '../api'
import { useDocumentNotes } from '../hooks/useDocumentNotes'
import { DocumentView } from './DocumentView'
import { FieldFilters } from './FieldFilters'
import { ScatterPlot } from './ScatterPlot'
import { StripPlot } from './StripPlot'
import type { StripOrientation } from './StripPlot'

type Mode = 'point2d' | 'fields'

// What gets drawn: a scatterplot (point_2d field, or two score axes), or a strip
// plot (one score axis, one categorical axis — a beeswarm per category, so
// documents sharing a category don't stack on a line). Axis labels and orientation
// are captured with the request, so they always match the points shown.
type PlotData =
  | { kind: 'scatter'; points: ScatterPoint[]; xLabel: string; yLabel: string }
  | {
      kind: 'strip'
      points: StripPoint[]
      orientation: StripOrientation
      scoreLabel: string
      categoryLabel: string
    }

// Field names created by SourceText's classification presets: if present, they make
// the most useful defaults for a strip plot (confidence per gold label, colored by
// prediction).
const PRESET_SCORE = 'predictions_confidence'
const PRESET_CATEGORIES = ['gold_labels', 'predictions']
const PRESET_COLOR = 'predictions'

const isCategorical = (field: Field | undefined) =>
  field?.type === 'label' || field?.type === 'group'

function pickDefault(names: string[], preferred: string[]): string | null {
  return preferred.find((name) => names.includes(name)) ?? names[0] ?? null
}

export function PlotView() {
  // The full field list, for the DocumentView detail pane and the filter controls.
  const [fields, setFields] = useState<Field[] | null>(null)
  // Only the fields the plot can use, for the mode/axis/color selectors.
  const [plotFields, setPlotFields] = useState<Field[]>([])
  const [mode, setMode] = useState<Mode>('point2d')
  const [pointField, setPointField] = useState<string | null>(null)
  const [xField, setXField] = useState<string | null>(null)
  const [yField, setYField] = useState<string | null>(null)
  const [colorField, setColorField] = useState<string | null>(null)
  // Independent from the other views' filter state.
  const [filters, setFilters] = useState<FieldFilter[]>([])
  const [data, setData] = useState<PlotData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const { currentNotes, handleNotesChange, handleNotesSave } = useDocumentNotes(
    selected,
    setError,
  )

  // Load the full field list and the plottable fields once, then choose sensible
  // defaults for the mode/axis selectors.
  useEffect(() => {
    fetchFields()
      .then(setFields)
      .catch((err: Error) => setError(err.message))
    fetchScatter({})
      .then((result) => {
        setPlotFields(result.fields)
        const names = (type: Field['type'][]) =>
          result.fields.filter((f) => type.includes(f.type)).map((f) => f.name)
        const point2d = names(['point_2d'])
        const scores = names(['score'])
        const categories = names(['label', 'group'])

        if (point2d.length > 0) setPointField(point2d[0])
        if (scores.length >= 2) {
          setXField(scores[0])
          setYField(scores[1])
        } else if (scores.length === 1 && categories.length > 0) {
          const category = pickDefault(categories, PRESET_CATEGORIES)
          setXField(pickDefault(scores, [PRESET_SCORE]))
          setYField(category)
          if (category !== PRESET_COLOR && categories.includes(PRESET_COLOR)) {
            setColorField(PRESET_COLOR)
          }
        }
        setMode(point2d.length > 0 ? 'point2d' : 'fields')
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  const fieldByName = (name: string | null) =>
    plotFields.find((f) => f.name === name)
  const xCategorical = isCategorical(fieldByName(xField))
  const yCategorical = isCategorical(fieldByName(yField))

  // Refetch points whenever the active selection changes.
  useEffect(() => {
    let stale = false
    const color = colorField ? { colorField } : {}
    const filtersQuery = filters.length > 0 ? { filters } : {}
    let request: Promise<PlotData> | null = null
    if (mode === 'point2d' && pointField) {
      request = fetchScatter({
        field: pointField,
        ...color,
        ...filtersQuery,
      }).then((r) => ({
        kind: 'scatter',
        points: r.points,
        xLabel: 'x',
        yLabel: 'y',
      }))
    } else if (mode === 'fields' && xField && yField) {
      if (!xCategorical && !yCategorical) {
        request = fetchScatter({
          xField,
          yField,
          ...color,
          ...filtersQuery,
        }).then((r) => ({
          kind: 'scatter',
          points: r.points,
          xLabel: xField,
          yLabel: yField,
        }))
      } else if (xCategorical !== yCategorical) {
        const [scoreField, categoryField] = xCategorical
          ? [yField, xField]
          : [xField, yField]
        request = fetchStrip({
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
        }))
      }
    }
    // Nothing to fetch (e.g. both axes categorical): the render shows a hint instead.
    if (!request) return
    request
      .then((result) => !stale && setData(result))
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [
    mode,
    pointField,
    xField,
    yField,
    xCategorical,
    yCategorical,
    colorField,
    filters,
  ])

  const handleSelect = (documentId: string) => {
    fetchDocument(documentId)
      .then(setSelected)
      .catch((err: Error) => setError(err.message))
  }

  if (!fields) return null

  const point2dFields = plotFields.filter((f) => f.type === 'point_2d')
  const scoreFields = plotFields.filter((f) => f.type === 'score')
  const categoryFields = plotFields.filter(isCategorical)
  const hasPlottableFields =
    point2dFields.length > 0 ||
    scoreFields.length >= 2 ||
    (scoreFields.length >= 1 && categoryFields.length > 0)
  const axisOptions = [
    { group: 'Scores', items: scoreFields.map((f) => f.name) },
    { group: 'Categories', items: categoryFields.map((f) => f.name) },
  ].filter((g) => g.items.length > 0)
  const bothCategorical = mode === 'fields' && xCategorical && yCategorical

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack h="100%">
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {!hasPlottableFields && (
            <Text c="dimmed">
              Nothing to plot: needs a point_2d field, or a score field plus
              another score, label or group field.
            </Text>
          )}
          {hasPlottableFields && (
            <>
              <Group>
                {point2dFields.length > 0 && axisOptions.length > 0 && (
                  <Select
                    label="Mode"
                    data={[
                      { value: 'point2d', label: '2D Point' },
                      { value: 'fields', label: 'Fields' },
                    ]}
                    value={mode}
                    onChange={(value) => value && setMode(value as Mode)}
                    allowDeselect={false}
                  />
                )}
                {mode === 'point2d' && (
                  <Select
                    label="Field"
                    data={point2dFields.map((f) => f.name)}
                    value={pointField}
                    onChange={setPointField}
                    allowDeselect={false}
                  />
                )}
                {mode === 'fields' && (
                  <>
                    <Select
                      label="X"
                      data={axisOptions}
                      value={xField}
                      onChange={setXField}
                      allowDeselect={false}
                    />
                    <Select
                      label="Y"
                      data={axisOptions}
                      value={yField}
                      onChange={setYField}
                      allowDeselect={false}
                    />
                  </>
                )}
                {categoryFields.length > 0 && (
                  <Select
                    label="Color by"
                    placeholder="None"
                    data={categoryFields.map((f) => f.name)}
                    value={colorField}
                    onChange={setColorField}
                    clearable
                  />
                )}
              </Group>
              <FieldFilters
                fields={fields}
                filters={filters}
                onChange={setFilters}
              />
              {bothCategorical && (
                <Text c="dimmed">
                  Both axes are categorical. Pick a score for one of them, or
                  use the confusion matrix view to cross two categories.
                </Text>
              )}
              {!bothCategorical && !data && <Loader />}
              {!bothCategorical && data?.kind === 'scatter' && (
                <ScatterPlot
                  points={data.points}
                  xLabel={data.xLabel}
                  yLabel={data.yLabel}
                  selectedId={selected?.id ?? null}
                  onSelect={handleSelect}
                />
              )}
              {!bothCategorical && data?.kind === 'strip' && (
                <StripPlot
                  points={data.points}
                  orientation={data.orientation}
                  scoreLabel={data.scoreLabel}
                  categoryLabel={data.categoryLabel}
                  selectedId={selected?.id ?? null}
                  onSelect={handleSelect}
                />
              )}
            </>
          )}
        </Stack>
      </Box>
      <Box
        flex={2}
        p="md"
        style={{
          overflowY: 'auto',
          borderLeft: '1px solid var(--mantine-color-default-border)',
        }}
      >
        <DocumentView
          fields={fields}
          document={selected}
          notes={currentNotes}
          onNotesSave={handleNotesSave}
          onNotesChange={handleNotesChange}
        />
      </Box>
    </Flex>
  )
}

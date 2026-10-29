import { Box, Flex, Group, Loader, Select, Stack, Text } from '@mantine/core'
import { useMemo, useState } from 'react'

import type { Filter } from '../../api/types'
import { ErrorAlert } from '../../common/ErrorAlert'
import { DocumentView } from '../../document/DocumentView'
import { FieldFilters } from '../../fields/FieldFilters'
import { useFields } from '../../hooks/useFields'
import { defaultPlotSelection, isCategorical } from './plotDefaults'
import type { Mode, PlotSelection } from './plotDefaults'
import { ScatterPlot } from './ScatterPlot'
import { StripPlot } from './StripPlot'
import { useDocument } from './useDocument'
import { usePlotData } from './usePlotData'
import { usePlotFields } from './usePlotFields'

export function PlotView() {
  // The full field list, for the DocumentView detail pane and the filter controls.
  const { fields, error: fieldsError } = useFields()
  // Only the fields the plot can use, for the mode/axis/color selectors.
  const { plotFields: loadedPlotFields, error: plotFieldsError } =
    usePlotFields()
  const plotFields = useMemo(() => loadedPlotFields ?? [], [loadedPlotFields])
  // What's picked in the selectors (a cleared color is null); the rest comes from
  // the defaults.
  const [choice, setChoice] = useState<Partial<PlotSelection>>({})
  const defaults = useMemo(() => defaultPlotSelection(plotFields), [plotFields])
  const selection = { ...defaults, ...choice }
  const { mode, pointField, xField, yField, colorField } = selection
  const choose =
    <K extends keyof PlotSelection>(key: K) =>
    (value: PlotSelection[K]) =>
      setChoice((current) => ({ ...current, [key]: value }))
  // Independent from the other views' filter state.
  const [filters, setFilters] = useState<Filter[]>([])
  const { data, error: dataError } = usePlotData(selection, plotFields, filters)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { document: selected, error: documentError } = useDocument(selectedId)
  const error = fieldsError ?? plotFieldsError ?? dataError ?? documentError

  const fieldByName = (name: string | null) =>
    plotFields.find((f) => f.name === name)
  const xCategorical = isCategorical(fieldByName(xField))
  const yCategorical = isCategorical(fieldByName(yField))

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
          <ErrorAlert error={error} />
          {!hasPlottableFields && (
            <Text c="dimmed">
              Nothing to plot: needs a point_2d field, or a score field plus
              another score or label field.
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
                    onChange={(value) => value && choose('mode')(value as Mode)}
                    allowDeselect={false}
                  />
                )}
                {mode === 'point2d' && (
                  <Select
                    label="Field"
                    data={point2dFields.map((f) => f.name)}
                    value={pointField}
                    onChange={choose('pointField')}
                    allowDeselect={false}
                  />
                )}
                {mode === 'fields' && (
                  <>
                    <Select
                      label="X"
                      data={axisOptions}
                      value={xField}
                      onChange={choose('xField')}
                      allowDeselect={false}
                    />
                    <Select
                      label="Y"
                      data={axisOptions}
                      value={yField}
                      onChange={choose('yField')}
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
                    onChange={choose('colorField')}
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
                  colorDefinitions={data.colorDefinitions}
                  selectedId={selected?.id ?? null}
                  onSelect={setSelectedId}
                />
              )}
              {!bothCategorical && data?.kind === 'strip' && (
                <StripPlot
                  points={data.points}
                  orientation={data.orientation}
                  scoreLabel={data.scoreLabel}
                  categoryLabel={data.categoryLabel}
                  categoryDefinitions={data.categoryDefinitions}
                  colorDefinitions={data.colorDefinitions}
                  selectedId={selected?.id ?? null}
                  onSelect={setSelectedId}
                />
              )}
            </>
          )}
        </Stack>
      </Box>
      <DocumentView fields={fields} document={selected} filters={filters} />
    </Flex>
  )
}

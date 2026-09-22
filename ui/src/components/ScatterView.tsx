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

import { fetchDocument, fetchFields, fetchScatter } from '../api'
import type { Document, Field, FieldFilter, ScatterData } from '../api'
import { useDocumentNotes } from '../hooks/useDocumentNotes'
import { DocumentView } from './DocumentView'
import { FieldFilters } from './FieldFilters'
import { ScatterPlot } from './ScatterPlot'

type Mode = 'point2d' | 'pair'

export function ScatterView() {
  // The full field list, for the DocumentView detail pane (mirrors TabularView) and
  // for the filter controls (which aren't limited to the plottable fields below).
  const [fields, setFields] = useState<Field[] | null>(null)
  // Only the point_2d/score fields, for the mode/field selector controls.
  const [scatterFields, setScatterFields] = useState<Field[]>([])
  const [mode, setMode] = useState<Mode>('point2d')
  const [pointField, setPointField] = useState<string | null>(null)
  const [xField, setXField] = useState<string | null>(null)
  const [yField, setYField] = useState<string | null>(null)
  const [colorField, setColorField] = useState<string | null>(null)
  // Independent from TabularView's filter state — narrowing the scatterplot doesn't
  // affect the table, and vice versa.
  const [filters, setFilters] = useState<FieldFilter[]>([])
  const [data, setData] = useState<ScatterData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const { currentNotes, handleNotesChange, handleNotesSave } = useDocumentNotes(
    selected,
    setError,
  )

  // Load the full field list and the scatter-plottable fields once, then choose
  // sensible defaults for the mode/field selectors.
  useEffect(() => {
    fetchFields()
      .then(setFields)
      .catch((err: Error) => setError(err.message))
    fetchScatter({})
      .then((result) => {
        setScatterFields(result.fields)
        const point2dFields = result.fields.filter((f) => f.type === 'point_2d')
        const scoreFields = result.fields.filter((f) => f.type === 'score')

        if (point2dFields.length > 0) {
          setPointField(point2dFields[0].name)
        }
        if (scoreFields.length >= 2) {
          setXField(scoreFields[0].name)
          setYField(scoreFields[1].name)
        }

        setMode(point2dFields.length > 0 ? 'point2d' : 'pair')
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  // Refetch points whenever the active selection changes.
  useEffect(() => {
    const colorFieldQuery = colorField ? { colorField } : {}
    const filtersQuery = filters.length > 0 ? { filters } : {}
    if (mode === 'point2d' && pointField) {
      fetchScatter({ field: pointField, ...colorFieldQuery, ...filtersQuery })
        .then(setData)
        .catch((err: Error) => setError(err.message))
    } else if (mode === 'pair' && xField && yField) {
      fetchScatter({ xField, yField, ...colorFieldQuery, ...filtersQuery })
        .then(setData)
        .catch((err: Error) => setError(err.message))
    }
  }, [mode, pointField, xField, yField, colorField, filters])

  const handleSelect = (documentId: string) => {
    fetchDocument(documentId)
      .then(setSelected)
      .catch((err: Error) => setError(err.message))
  }

  if (!fields) return null

  const point2dFields = scatterFields.filter((f) => f.type === 'point_2d')
  const scoreFields = scatterFields.filter((f) => f.type === 'score')
  const groupFields = scatterFields.filter((f) => f.type === 'group')
  const hasScatterableFields =
    point2dFields.length > 0 || scoreFields.length >= 2

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack h="100%">
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {!hasScatterableFields && (
            <Text c="dimmed">
              No point_2d or score fields available for a scatterplot.
            </Text>
          )}
          {hasScatterableFields && (
            <>
              <Group>
                {point2dFields.length > 0 && scoreFields.length >= 2 && (
                  <Select
                    label="Mode"
                    data={[
                      { value: 'point2d', label: '2D Point' },
                      { value: 'pair', label: 'Score pair' },
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
                {mode === 'pair' && (
                  <>
                    <Select
                      label="X"
                      data={scoreFields.map((f) => f.name)}
                      value={xField}
                      onChange={setXField}
                      allowDeselect={false}
                    />
                    <Select
                      label="Y"
                      data={scoreFields.map((f) => f.name)}
                      value={yField}
                      onChange={setYField}
                      allowDeselect={false}
                    />
                  </>
                )}
                {groupFields.length > 0 && (
                  <Select
                    label="Color by"
                    placeholder="None"
                    data={groupFields.map((f) => f.name)}
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
              {!data && <Loader />}
              {data && (
                <ScatterPlot
                  points={data.points}
                  xLabel={mode === 'pair' ? (xField ?? 'x') : 'x'}
                  yLabel={mode === 'pair' ? (yField ?? 'y') : 'y'}
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

import {
  Alert,
  Box,
  Flex,
  Group,
  Pagination,
  Select,
  Stack,
  Text,
} from '@mantine/core'
import { useEffect, useState } from 'react'

import {
  fetchCrosstab,
  fetchFields,
  fetchTabularDocuments,
  PAGE_SIZE,
} from '../api'
import type {
  CrosstabCell,
  Document,
  DocumentsPage,
  Field,
  FieldFilter,
  Sort,
} from '../api'
import { useDocumentNotes } from '../hooks/useDocumentNotes'
import { ConfusionMatrix } from './ConfusionMatrix'
import type { MatrixCell } from './ConfusionMatrix'
import { DocumentTable } from './DocumentTable'
import { DocumentView } from './DocumentView'
import { FieldFilters } from './FieldFilters'

// Field names created by SourceText's classification presets: if present, the
// matrix opens as gold labels (rows) vs. predictions (columns).
const PRESET_ROW = 'gold_labels'
const PRESET_COL = 'predictions'

export function MatrixView() {
  // The full field list, for the DocumentView detail pane and the field selectors.
  const [fields, setFields] = useState<Field[] | null>(null)
  const [rowField, setRowField] = useState<string | null>(null)
  const [colField, setColField] = useState<string | null>(null)
  const [cells, setCells] = useState<CrosstabCell[] | null>(null)
  const [cell, setCell] = useState<MatrixCell | null>(null)
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<Sort | null>(null)
  // Filters on the table's columns. They narrow only the listed documents, not the
  // matrix counts, and carry over when another cell is selected.
  const [filters, setFilters] = useState<FieldFilter[]>([])
  const [documents, setDocuments] = useState<DocumentsPage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const { currentNotes, handleNotesChange, handleNotesSave } = useDocumentNotes(
    selected,
    setError,
  )

  useEffect(() => {
    fetchFields()
      .then((result) => {
        setFields(result)
        const names = result
          .filter((f) => f.type === 'label' || f.type === 'group')
          .map((f) => f.name)
        if (names.includes(PRESET_ROW) && names.includes(PRESET_COL)) {
          setRowField(PRESET_ROW)
          setColField(PRESET_COL)
        } else if (names.length >= 2) {
          setRowField(names[0])
          setColField(names[1])
        }
      })
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!rowField || !colField) return
    let stale = false
    fetchCrosstab(rowField, colField)
      .then((result) => !stale && setCells(result))
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [rowField, colField])

  // The documents in the selected cell: the tabular route, pre-filtered to that
  // cell's two values on top of the table's own filters.
  useEffect(() => {
    if (!rowField || !colField || !cell) return
    let stale = false
    fetchTabularDocuments(page, sort, [
      ...filters,
      { field: rowField, op: 'in', values: [cell.row] },
      { field: colField, op: 'in', values: [cell.col] },
    ])
      .then((result) => !stale && setDocuments(result))
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [rowField, colField, cell, page, sort, filters])

  // Changing either field invalidates the selected cell, and the table filters
  // (which may target the newly chosen field).
  const changeField =
    (setter: (value: string | null) => void) => (value: string | null) => {
      setter(value)
      setCells(null)
      setCell(null)
      setDocuments(null)
      setFilters([])
    }

  const handleFiltersChange: typeof setFilters = (value) => {
    setFilters(value)
    setPage(1)
  }

  const handleCellSelect = (next: MatrixCell) => {
    setCell(next)
    setPage(1)
  }

  const handleSort = (field: string) => {
    setSort((current) => {
      if (current?.field !== field) return { field, dir: 'asc' }
      if (current.dir === 'asc') return { field, dir: 'desc' }
      return null
    })
    setPage(1)
  }

  if (!fields) return null

  const categoryFields = fields
    .filter((f) => f.type === 'label' || f.type === 'group')
    .map((f) => f.name)
  // Every document in the table shares the matrix fields' values, so those
  // columns would only repeat the selected cell (and filtering on them would only
  // fight it).
  const tableFields = fields.filter(
    (f) => f.name !== rowField && f.name !== colField,
  )
  const cellTotal =
    cells?.find((c) => c.row === cell?.row && c.col === cell?.col)?.count ?? 0

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack>
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {categoryFields.length < 2 && (
            <Text c="dimmed">
              A confusion matrix needs two label or group fields, e.g.
              predictions and gold labels.
            </Text>
          )}
          {categoryFields.length >= 2 && (
            <>
              <Group>
                <Select
                  label="Rows"
                  data={categoryFields}
                  value={rowField}
                  onChange={changeField(setRowField)}
                  allowDeselect={false}
                />
                <Select
                  label="Columns"
                  data={categoryFields}
                  value={colField}
                  onChange={changeField(setColField)}
                  allowDeselect={false}
                />
              </Group>
              {cells && rowField && colField && (
                <ConfusionMatrix
                  rowField={rowField}
                  colField={colField}
                  cells={cells}
                  selected={cell}
                  onSelect={handleCellSelect}
                />
              )}
              {!cell && (
                <Text c="dimmed" size="sm" ta="center">
                  Click a cell to list its documents.
                </Text>
              )}
              {cell && documents && (
                <>
                  <FieldFilters
                    fields={tableFields}
                    filters={filters}
                    onChange={handleFiltersChange}
                  />
                  <Text size="sm">
                    {filters.length > 0
                      ? `${documents.total} of ${cellTotal}`
                      : documents.total}{' '}
                    documents with {rowField} = <b>{cell.row}</b> and {colField}{' '}
                    = <b>{cell.col}</b>
                  </Text>
                  <DocumentTable
                    fields={tableFields}
                    documents={documents.documents}
                    selectedId={selected?.id ?? null}
                    onSelect={setSelected}
                    sort={sort}
                    onSort={handleSort}
                  />
                  {documents.total > PAGE_SIZE && (
                    <Pagination
                      value={page}
                      onChange={setPage}
                      total={Math.ceil(documents.total / PAGE_SIZE)}
                    />
                  )}
                </>
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

import {
  Box,
  Flex,
  Group,
  Pagination,
  Select,
  Stack,
  Text,
} from '@mantine/core'
import { useMemo, useState } from 'react'

import { PAGE_SIZE } from '../../api/documents'
import type { Document, Filter } from '../../api/types'
import { DocumentTable } from '../../common/DocumentTable'
import { ErrorAlert } from '../../common/ErrorAlert'
import { DocumentView } from '../../document/DocumentView'
import { FieldFilters } from '../../fields/FieldFilters'
import { useDocumentsPage } from '../../hooks/useDocumentsPage'
import { useFields } from '../../hooks/useFields'
import { ConfusionMatrix } from './ConfusionMatrix'
import type { MatrixCell } from './ConfusionMatrix'
import { defaultMatrixFields } from './matrixDefaults'
import { useCrosstab } from './useCrosstab'

export function MatrixView() {
  // The full field list, for the DocumentView detail pane and the field selectors.
  const { fields, error: fieldsError } = useFields()
  // The fields picked in the selectors; until then, the defaults.
  const [rowChoice, setRowChoice] = useState<string | null>(null)
  const [colChoice, setColChoice] = useState<string | null>(null)
  const defaults = useMemo(
    () => (fields ? defaultMatrixFields(fields) : null),
    [fields],
  )
  const rowField = rowChoice ?? defaults?.row ?? null
  const colField = colChoice ?? defaults?.col ?? null
  const { cells, error: cellsError } = useCrosstab(rowField, colField)
  const [cell, setCell] = useState<MatrixCell | null>(null)
  // Filters on the table's columns. They narrow only the listed documents, not the
  // matrix counts, and carry over when another cell is selected.
  const [filters, setFilters] = useState<Filter[]>([])

  // The documents in the selected cell: the tabular route, pre-filtered to that
  // cell's two values on top of the table's own filters.
  const documentFilters = useMemo(
    (): Filter[] | null =>
      rowField && colField && cell
        ? [
            ...filters,
            { field: rowField, op: 'in', values: [cell.row] },
            { field: colField, op: 'in', values: [cell.col] },
          ]
        : null,
    [rowField, colField, cell, filters],
  )
  const {
    data: documents,
    error: documentsError,
    page,
    setPage,
    sort,
    toggleSort,
  } = useDocumentsPage(documentFilters)
  const error = fieldsError ?? cellsError ?? documentsError
  const [selected, setSelected] = useState<Document | null>(null)

  // Changing either field invalidates the selected cell, and the table filters
  // (which may target the newly chosen field).
  const changeField =
    (setter: (value: string | null) => void) => (value: string | null) => {
      setter(value)
      setCell(null)
      setFilters([])
    }

  if (!fields) return null

  const definitionsOf = (name: string) =>
    fields.find((f) => f.name === name)?.definitions
  const categoryFields = fields
    .filter((f) => f.type === 'label')
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
          <ErrorAlert error={error} />
          {categoryFields.length < 2 && (
            <Text c="dimmed">
              A confusion matrix needs two label fields, e.g. predictions and
              gold labels.
            </Text>
          )}
          {categoryFields.length >= 2 && (
            <>
              <Group>
                <Select
                  label="Rows"
                  data={categoryFields}
                  value={rowField}
                  onChange={changeField(setRowChoice)}
                  allowDeselect={false}
                />
                <Select
                  label="Columns"
                  data={categoryFields}
                  value={colField}
                  onChange={changeField(setColChoice)}
                  allowDeselect={false}
                />
              </Group>
              {cells && rowField && colField && (
                <ConfusionMatrix
                  rowField={rowField}
                  colField={colField}
                  rowDefinitions={definitionsOf(rowField)}
                  colDefinitions={definitionsOf(colField)}
                  cells={cells}
                  selected={cell}
                  onSelect={setCell}
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
                    onChange={setFilters}
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
                    onSort={toggleSort}
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
      <DocumentView fields={fields} document={selected} filters={filters} />
    </Flex>
  )
}

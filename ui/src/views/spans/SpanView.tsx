import {
  Alert,
  Box,
  Flex,
  Pagination,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
} from '@mantine/core'
import { useEffect, useMemo, useState } from 'react'

import {
  fetchFields,
  fetchTabularDocuments,
  PAGE_SIZE,
} from '../../api/documents'
import type { DocumentsPage } from '../../api/documents'
import { fetchSpanSummary } from '../../api/spans'
import type { SpanSummary, SpanTypeSummary } from '../../api/spans'
import type {
  Document,
  Field,
  FieldFilter,
  Filter,
  Sort,
} from '../../api/types'
import { DocumentTable } from '../../common/DocumentTable'
import { DocumentView } from '../../document/DocumentView'
import { FieldFilters, SpanFilter } from '../../fields/FieldFilters'
import { SpanBadge } from '../../fields/span/SpanBadge'

// Find documents by their spans: narrow a span field's spans by label, score and
// text, then pick a span type to list the documents containing it, with its spans
// highlighted in the document.
export function SpanView() {
  // The full field list, for the DocumentView detail pane and the filters.
  const [fields, setFields] = useState<Field[] | null>(null)
  const [spanField, setSpanField] = useState<string | null>(null)
  // Every filter, including the span filter on `spanField` (labels, score, search),
  // which prunes the spans counted, listed and highlighted.
  const [filters, setFilters] = useState<Filter[]>([])
  const [selectedType, setSelectedType] = useState<SpanTypeSummary | null>(null)
  const [summary, setSummary] = useState<SpanSummary | null>(null)
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<Sort | null>(null)
  const [documents, setDocuments] = useState<DocumentsPage | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFields()
      .then(setFields)
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(() => {
    let stale = false
    fetchSpanSummary(spanField, filters)
      .then((result) => {
        if (stale) return
        setSummary(result)
        if (result.field !== spanField) setSpanField(result.field)
        setError(null)
      })
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [spanField, filters])

  const spanFilter = filters.find(
    (f): f is FieldFilter => f.op === 'span' && f.field === spanField,
  )

  // The documents with a matching span: the span filter (always present, so only
  // documents with a span in the field are listed), narrowed to the selected type.
  const documentFilters = useMemo(() => {
    if (!spanField) return null
    const base: FieldFilter = spanFilter ?? { field: spanField, op: 'span' }
    const narrowed: FieldFilter = selectedType
      ? { ...base, typeText: selectedType.text, values: [selectedType.label] }
      : base
    return [...filters.filter((f) => f !== spanFilter), narrowed]
  }, [filters, spanField, spanFilter, selectedType])

  useEffect(() => {
    if (!documentFilters) return
    let stale = false
    fetchTabularDocuments(page, sort, documentFilters)
      .then((result) => !stale && setDocuments(result))
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [documentFilters, page, sort])

  const handleFieldChange = (value: string | null) => {
    setSpanField(value)
    setSelectedType(null)
    setPage(1)
  }

  // Any filter change may drop the selected type's spans, so it's deselected.
  const handleFiltersChange: typeof setFilters = (value) => {
    setFilters(value)
    setSelectedType(null)
    setPage(1)
  }

  const handleTypeSelect = (type: SpanTypeSummary) => {
    const same =
      selectedType?.text === type.text && selectedType.label === type.label
    setSelectedType(same ? null : type)
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

  if (!fields || !summary) {
    return error ? (
      <Alert color="red" title="Something went wrong" m="md">
        {error}
      </Alert>
    ) : null
  }

  const field = fields.find((f) => f.name === spanField)
  const labelCounts = new Map(summary.labels.map((l) => [l.label, l.spans]))

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack>
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {!field && (
            <Text c="dimmed">
              No span fields. Pass a SpanType field (e.g. NER output) to find
              documents by their spans.
            </Text>
          )}
          {field && (
            <>
              <FieldFilters
                fields={fields.filter((f) => f.name !== field.name)}
                filters={filters}
                onChange={handleFiltersChange}
              />
              {summary.fields.length > 1 && (
                <Select
                  label="Span field"
                  data={summary.fields}
                  value={spanField}
                  onChange={handleFieldChange}
                  allowDeselect={false}
                  w="fit-content"
                />
              )}
              <SpanFilter
                key={field.name}
                field={field}
                current={spanFilter}
                onChange={handleFiltersChange}
                labelCounts={labelCounts}
              />
              <SpanTypeTable
                types={summary.types}
                selected={selectedType}
                onSelect={handleTypeSelect}
              />
              {summary.totalTypes > summary.types.length && (
                <Text size="xs" c="dimmed">
                  Showing the {summary.types.length} most frequent of{' '}
                  {summary.totalTypes} span types. Search to find others.
                </Text>
              )}
              {documents && (
                <>
                  <Text size="sm">
                    {documents.total} documents with{' '}
                    {selectedType ? (
                      <SpanBadge
                        text={selectedType.text}
                        label={selectedType.label}
                      />
                    ) : (
                      `a matching ${field.name} span`
                    )}
                  </Text>
                  <DocumentTable
                    fields={fields}
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
      <DocumentView
        fields={fields}
        document={selected}
        filters={filters}
        highlightType={
          selectedType && spanField
            ? {
                field: spanField,
                text: selectedType.text,
                label: selectedType.label,
              }
            : null
        }
      />
    </Flex>
  )
}

interface SpanTypeTableProps {
  types: SpanTypeSummary[]
  selected: SpanTypeSummary | null
  onSelect: (type: SpanTypeSummary) => void
}

function SpanTypeTable({ types, selected, onSelect }: SpanTypeTableProps) {
  if (types.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        No matching spans.
      </Text>
    )
  }
  return (
    <ScrollArea.Autosize mah={280}>
      <Table highlightOnHover stickyHeader>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Span type</Table.Th>
            <Table.Th ta="right">Spans</Table.Th>
            <Table.Th ta="right">Documents</Table.Th>
            <Table.Th ta="right">Forms</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {types.map((type) => {
            const isSelected =
              selected?.text === type.text && selected.label === type.label
            return (
              <Table.Tr
                key={`${type.label}\u0000${type.text}`}
                onClick={() => onSelect(type)}
                bg={
                  isSelected ? 'var(--mantine-primary-color-light)' : undefined
                }
                style={{ cursor: 'pointer' }}
              >
                <Table.Td>
                  <SpanBadge text={type.text} label={type.label} />
                </Table.Td>
                <Table.Td ta="right">{type.spans}</Table.Td>
                <Table.Td ta="right">{type.documents}</Table.Td>
                <Table.Td ta="right">{type.variants}</Table.Td>
              </Table.Tr>
            )
          })}
        </Table.Tbody>
      </Table>
    </ScrollArea.Autosize>
  )
}

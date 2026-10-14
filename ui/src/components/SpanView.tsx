import {
  Alert,
  Badge,
  Box,
  Chip,
  Flex,
  Group,
  Input,
  Pagination,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { IconSearch } from '@tabler/icons-react'
import { useEffect, useState } from 'react'

import {
  fetchDocumentSpans,
  fetchFields,
  fetchSpanSummary,
  fetchTabularDocuments,
  PAGE_SIZE,
} from '../api'
import type {
  Document,
  DocumentsPage,
  Field,
  FieldFilter,
  Sort,
  Span,
  SpanSummary,
  SpanText,
} from '../api'
import { DocumentTable } from './DocumentTable'
import { DocumentView } from './DocumentView'
import { FieldFilters } from './FieldFilters'

// The chip value standing for "no label selected" (Chip.Group needs a string).
const ALL_LABELS = ''

// Find documents by their spans: pick a label, or search for and pick a span text,
// to list the documents containing it, with those spans marked in the document.
export function SpanView() {
  // The full field list, for the DocumentView detail pane and the filters.
  const [fields, setFields] = useState<Field[] | null>(null)
  const [spanField, setSpanField] = useState<string | null>(null)
  const [label, setLabel] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [debouncedQuery] = useDebouncedValue(query, 250)
  const [spanText, setSpanText] = useState<SpanText | null>(null)
  // Filters on the other fields. They narrow the span counts and the documents.
  const [filters, setFilters] = useState<FieldFilter[]>([])
  const [summary, setSummary] = useState<SpanSummary | null>(null)
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<Sort | null>(null)
  const [documents, setDocuments] = useState<DocumentsPage | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const [selectedSpans, setSelectedSpans] = useState<Span[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchFields()
      .then(setFields)
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(() => {
    let stale = false
    fetchSpanSummary({
      field: spanField ?? undefined,
      label: label ?? undefined,
      q: debouncedQuery,
      filters,
    })
      .then((result) => {
        if (stale) return
        setSummary(result)
        setSpanField(result.field)
        setError(null)
      })
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [spanField, label, debouncedQuery, filters])

  // The documents with a span matching the selected label and/or text: the
  // tabular route with a "span" filter on top of the other fields' filters.
  const spanLabel = spanText?.label ?? label
  useEffect(() => {
    if (!spanField) return
    let stale = false
    const spanFilter: FieldFilter = {
      field: spanField,
      op: 'span',
      ...(spanLabel !== null && { values: [spanLabel] }),
      ...(spanText && { text: spanText.text }),
    }
    fetchTabularDocuments(page, sort, [...filters, spanFilter])
      .then((result) => !stale && setDocuments(result))
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [spanField, spanLabel, spanText, filters, page, sort])

  useEffect(() => {
    if (!selected) return
    let stale = false
    fetchDocumentSpans(selected.id)
      .then((spans) => !stale && setSelectedSpans(spans))
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [selected])

  const handleFieldChange = (value: string | null) => {
    setSpanField(value)
    setLabel(null)
    setSpanText(null)
    setPage(1)
  }

  const handleLabelChange = (value: string) => {
    const next = value === ALL_LABELS ? null : value
    setLabel(next)
    if (spanText && next !== null && spanText.label !== next) setSpanText(null)
    setPage(1)
  }

  const handleTextSelect = (row: SpanText) => {
    const same = spanText?.text === row.text && spanText.label === row.label
    setSpanText(same ? null : row)
    setPage(1)
  }

  const handleFiltersChange: typeof setFilters = (value) => {
    setFilters(value)
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

  // Marks the spans the documents were found by: those of the selected field,
  // label and text, or every span of the field if none is selected.
  const highlights = selected
    ? selectedSpans.filter(
        (s) =>
          s.field === spanField &&
          (spanLabel === null || s.label === spanLabel) &&
          (!spanText ||
            Array.from(selected.text).slice(s.start, s.end).join('') ===
              spanText.text),
      )
    : []
  const totalSpans = summary.labels.reduce((sum, l) => sum + l.spans, 0)

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack>
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {summary.fields.length === 0 && (
            <Text c="dimmed">
              No span fields. Pass a SpanType field (e.g. NER output) to find
              documents by their spans.
            </Text>
          )}
          {summary.fields.length > 0 && (
            <>
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
              <FieldFilters
                fields={fields}
                filters={filters}
                onChange={handleFiltersChange}
              />
              <Chip.Group
                value={label ?? ALL_LABELS}
                onChange={(value) => handleLabelChange(value as string)}
              >
                <Input.Wrapper label="Span labels">
                  <Group gap={6}>
                    <Chip value={ALL_LABELS} size="sm">
                      All <SpanCount n={totalSpans} />
                    </Chip>
                    {summary.labels.map((l) => (
                      <Chip key={l.label} value={l.label} size="sm">
                        {l.label} <SpanCount n={l.spans} />
                      </Chip>
                    ))}
                  </Group>
                </Input.Wrapper>
              </Chip.Group>
              <TextInput
                placeholder="Search span texts"
                leftSection={<IconSearch size={16} />}
                value={query}
                onChange={(event) => setQuery(event.currentTarget.value)}
              />
              <SpanTextTable
                texts={summary.texts}
                selected={spanText}
                onSelect={handleTextSelect}
                showLabel={label === null}
              />
              {summary.totalTexts > summary.texts.length && (
                <Text size="xs" c="dimmed">
                  Showing the {summary.texts.length} most frequent of{' '}
                  {summary.totalTexts} span texts. Search to find others.
                </Text>
              )}
              {documents && (
                <>
                  <Text size="sm">
                    {documents.total} documents with{' '}
                    {spanText ? (
                      <>
                        <b>{spanText.text}</b> as {spanText.label}
                      </>
                    ) : spanLabel !== null ? (
                      <>
                        a <b>{spanLabel}</b> span
                      </>
                    ) : (
                      `a ${spanField} span`
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
        highlights={highlights}
      />
    </Flex>
  )
}

function SpanCount({ n }: { n: number }) {
  return (
    <Text span size="xs" opacity={0.6}>
      {n}
    </Text>
  )
}

interface SpanTextTableProps {
  texts: SpanText[]
  selected: SpanText | null
  onSelect: (row: SpanText) => void
  // Off when one label is selected, since every row would repeat it.
  showLabel: boolean
}

function SpanTextTable({
  texts,
  selected,
  onSelect,
  showLabel,
}: SpanTextTableProps) {
  if (texts.length === 0) {
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
            <Table.Th>Span text</Table.Th>
            {showLabel && <Table.Th>Label</Table.Th>}
            <Table.Th ta="right">Spans</Table.Th>
            <Table.Th ta="right">Documents</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {texts.map((row) => {
            const isSelected =
              selected?.text === row.text && selected.label === row.label
            return (
              <Table.Tr
                key={`${row.label}\u0000${row.text}`}
                onClick={() => onSelect(row)}
                bg={
                  isSelected ? 'var(--mantine-primary-color-light)' : undefined
                }
                style={{ cursor: 'pointer' }}
              >
                <Table.Td maw={320}>
                  <Text size="sm" truncate>
                    {row.text}
                  </Text>
                </Table.Td>
                {showLabel && (
                  <Table.Td>
                    <Badge variant="light">{row.label}</Badge>
                  </Table.Td>
                )}
                <Table.Td ta="right">{row.spans}</Table.Td>
                <Table.Td ta="right">{row.documents}</Table.Td>
              </Table.Tr>
            )
          })}
        </Table.Tbody>
      </Table>
    </ScrollArea.Autosize>
  )
}

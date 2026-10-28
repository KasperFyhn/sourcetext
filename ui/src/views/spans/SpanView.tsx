import { Box, Flex, Pagination, Select, Stack, Text } from '@mantine/core'
import { useMemo, useState } from 'react'

import { PAGE_SIZE } from '../../api/documents'
import type { SpanTypeSummary } from '../../api/spans'
import type { Document, FieldFilter, Filter } from '../../api/types'
import { DocumentTable } from '../../common/DocumentTable'
import { ErrorAlert } from '../../common/ErrorAlert'
import { DocumentView } from '../../document/DocumentView'
import { FieldFilters } from '../../fields/FieldFilters'
import { SpanBadge } from '../../fields/span/SpanBadge'
import { SpanFilter } from '../../fields/span/SpanFilter'
import { useDocumentsPage } from '../../hooks/useDocumentsPage'
import { useFields } from '../../hooks/useFields'
import { SpanTypeTable } from './SpanTypeTable'
import { useSpanSummary } from './useSpanSummary'

// Find documents by their spans: narrow a span field's spans by label, score and
// text, then pick a span type to list the documents containing it, with its spans
// highlighted in the document.
export function SpanView() {
  // The full field list, for the DocumentView detail pane and the filters.
  const { fields, error: fieldsError } = useFields()
  // The span field picked in the selector; until then, the summary's default.
  const [spanFieldChoice, setSpanFieldChoice] = useState<string | null>(null)
  // Every filter, including the span filter on the span field (labels, score,
  // search), which prunes the spans counted, listed and highlighted.
  const [filters, setFilters] = useState<Filter[]>([])
  const [selectedType, setSelectedType] = useState<SpanTypeSummary | null>(null)
  const { summary, error: summaryError } = useSpanSummary(
    spanFieldChoice,
    filters,
  )
  const spanField = spanFieldChoice ?? summary?.field ?? null
  const [selected, setSelected] = useState<Document | null>(null)

  const spanFilter = filters.find(
    (f): f is FieldFilter => f.op === 'span' && f.field === spanField,
  )

  // The documents with a matching span: the span filter (always present, so only
  // documents with a span in the field are listed), narrowed to the selected type.
  // Any change here goes back to the first page.
  const documentFilters = useMemo(() => {
    if (!spanField) return null
    const base: FieldFilter = spanFilter ?? { field: spanField, op: 'span' }
    const narrowed: FieldFilter = selectedType
      ? { ...base, typeText: selectedType.text, values: [selectedType.label] }
      : base
    return [...filters.filter((f) => f !== spanFilter), narrowed]
  }, [filters, spanField, spanFilter, selectedType])
  const {
    data: documents,
    error: documentsError,
    page,
    setPage,
    sort,
    toggleSort,
  } = useDocumentsPage(documentFilters)
  const error = fieldsError ?? summaryError ?? documentsError

  const handleFieldChange = (value: string | null) => {
    setSpanFieldChoice(value)
    setSelectedType(null)
  }

  // Any filter change may drop the selected type's spans, so it's deselected.
  const handleFiltersChange: typeof setFilters = (value) => {
    setFilters(value)
    setSelectedType(null)
  }

  const handleTypeSelect = (type: SpanTypeSummary) => {
    const same =
      selectedType?.text === type.text && selectedType.label === type.label
    setSelectedType(same ? null : type)
  }

  if (!fields || !summary) {
    return <ErrorAlert error={error} m="md" />
  }

  const field = fields.find((f) => f.name === spanField)
  const labelCounts = new Map(summary.labels.map((l) => [l.label, l.spans]))

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack>
          <ErrorAlert error={error} />
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

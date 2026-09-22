import { Alert, Box, Flex, Loader, Pagination, Stack } from '@mantine/core'
import { useEffect, useState } from 'react'

import { fetchTabularDocuments, PAGE_SIZE } from '../api'
import type { Document, DocumentsPage, FieldFilter, Sort } from '../api'
import { useDocumentNotes } from '../hooks/useDocumentNotes'
import { DocumentTable } from './DocumentTable'
import { DocumentView } from './DocumentView'
import { FieldFilters } from './FieldFilters'

export function TabularView() {
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<Sort | null>(null)
  const [filters, setFilters] = useState<FieldFilter[]>([])
  const [data, setData] = useState<DocumentsPage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const { currentNotes, handleNotesChange, handleNotesSave } = useDocumentNotes(
    selected,
    setError,
  )

  useEffect(() => {
    let stale = false
    fetchTabularDocuments(page, sort, filters)
      .then((result) => {
        if (stale) return
        setData(result)
        setError(null)
      })
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [page, sort, filters])

  const handleSort = (field: string) => {
    setSort((current) => {
      if (current?.field !== field) return { field, dir: 'asc' }
      if (current.dir === 'asc') return { field, dir: 'desc' }
      return null
    })
    setPage(1)
  }

  const handleFiltersChange: typeof setFilters = (value) => {
    setFilters(value)
    setPage(1)
  }

  const fields = data?.fields ?? []

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack>
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {!error && !data && <Loader />}
          {data && (
            <>
              <FieldFilters
                fields={fields}
                filters={filters}
                onChange={handleFiltersChange}
              />
              <DocumentTable
                fields={fields}
                documents={data.documents}
                selectedId={selected?.id ?? null}
                onSelect={setSelected}
                sort={sort}
                onSort={handleSort}
              />
              <Pagination
                value={page}
                onChange={setPage}
                total={Math.max(1, Math.ceil(data.total / PAGE_SIZE))}
              />
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

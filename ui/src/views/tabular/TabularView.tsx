import { Box, Flex, Loader, Pagination, Stack } from '@mantine/core'
import { useState } from 'react'

import { PAGE_SIZE } from '../../api/documents'
import type { Document, Filter } from '../../api/types'
import { DocumentTable } from '../../common/DocumentTable'
import { ErrorAlert } from '../../common/ErrorAlert'
import { DocumentView } from '../../document/DocumentView'
import { FieldFilters } from '../../fields/FieldFilters'
import { useDocumentsPage } from '../../hooks/useDocumentsPage'

export function TabularView() {
  const [filters, setFilters] = useState<Filter[]>([])
  const { data, error, page, setPage, sort, toggleSort } =
    useDocumentsPage(filters)
  const [selected, setSelected] = useState<Document | null>(null)

  const fields = data?.fields ?? []

  return (
    <Flex h="100%">
      <Box flex={2} p="md" style={{ overflow: 'auto' }}>
        <Stack>
          <ErrorAlert error={error} />
          {!error && !data && <Loader />}
          {data && (
            <>
              <FieldFilters
                fields={fields}
                filters={filters}
                onChange={setFilters}
              />
              <DocumentTable
                fields={fields}
                documents={data.documents}
                selectedId={selected?.id ?? null}
                onSelect={setSelected}
                sort={sort}
                onSort={toggleSort}
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
      <DocumentView fields={fields} document={selected} filters={filters} />
    </Flex>
  )
}

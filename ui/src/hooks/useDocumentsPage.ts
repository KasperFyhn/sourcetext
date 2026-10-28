import { useState } from 'react'

import { fetchTabularDocuments } from '../api/documents'
import type { Filter, Sort } from '../api/types'
import { useFetch } from './useFetch'

// A page of the documents matching `filters` (null: nothing to list yet), with the
// page and sort state for a DocumentTable. New filters go back to the first page,
// so `filters` should only be a new array when the filters change.
export function useDocumentsPage(filters: Filter[] | null) {
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<Sort | null>(null)

  // Adjusted during render rather than in an effect, as React recommends, so the
  // fetch runs once, for page 1.
  const [prevFilters, setPrevFilters] = useState(filters)
  if (filters !== prevFilters) {
    setPrevFilters(filters)
    setPage(1)
  }

  const { data, error } = useFetch(
    filters ? () => fetchTabularDocuments(page, sort, filters) : null,
    [page, sort, filters],
  )

  // Ascending, then descending, then unsorted.
  const toggleSort = (field: string) => {
    setSort((current) => {
      if (current?.field !== field) return { field, dir: 'asc' }
      if (current.dir === 'asc') return { field, dir: 'desc' }
      return null
    })
    setPage(1)
  }

  return { data, error, page, setPage, sort, toggleSort }
}

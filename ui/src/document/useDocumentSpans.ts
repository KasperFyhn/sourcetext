import { fetchDocumentSpans } from '../api/spans'
import type { Span } from '../api/spans'
import type { Filter } from '../api/types'
import { useFetch } from '../hooks/useFetch'

const NO_SPANS: Span[] = []

// Every span on one document, pruned by the "span" filters among `filters`. Only
// those prune spans, so other filter changes don't refetch. Empty if loading fails.
export function useDocumentSpans(documentId: string, filters: Filter[]) {
  const spanFilters = JSON.stringify(filters.filter((f) => f.op === 'span'))
  const { data, error } = useFetch(
    () => fetchDocumentSpans(documentId, JSON.parse(spanFilters) as Filter[]),
    [documentId, spanFilters],
  )
  return error ? NO_SPANS : (data ?? NO_SPANS)
}

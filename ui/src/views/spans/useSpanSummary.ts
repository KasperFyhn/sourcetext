import { fetchSpanSummary } from '../../api/spans'
import type { Filter } from '../../api/types'
import { useFetch } from '../../hooks/useFetch'

// Counts per label and the most frequent span types of the span field `field`
// (null: the first one; the summary says which it picked).
export function useSpanSummary(field: string | null, filters: Filter[]) {
  const { data, error } = useFetch(
    () => fetchSpanSummary(field, filters),
    [field, filters],
  )
  return { summary: data, error }
}

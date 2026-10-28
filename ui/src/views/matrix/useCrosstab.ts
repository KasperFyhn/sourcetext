import { fetchCrosstab } from '../../api/matrix'
import { useFetch } from '../../hooks/useFetch'

// The matrix cells for two label fields. Null while another pair's cells would
// still show, so they're never drawn under the new fields' names.
export function useCrosstab(rowField: string | null, colField: string | null) {
  const { data, error } = useFetch(
    rowField && colField ? () => fetchCrosstab(rowField, colField) : null,
    [rowField, colField],
    { keepPrevious: false },
  )
  return { cells: data, error }
}

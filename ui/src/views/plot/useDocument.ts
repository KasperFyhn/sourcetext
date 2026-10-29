import { fetchDocument } from '../../api/documents'
import { useFetch } from '../../hooks/useFetch'

// One document with its field values, e.g. the one clicked in a plot.
export function useDocument(documentId: string | null) {
  const { data, error } = useFetch(
    documentId ? () => fetchDocument(documentId) : null,
    [documentId],
  )
  return { document: data, error }
}

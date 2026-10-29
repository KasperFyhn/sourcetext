import { fetchFields } from '../api/documents'
import { useFetch } from './useFetch'

// The full field list, for views that don't otherwise load a page of documents.
export function useFields() {
  const { data, error } = useFetch(fetchFields, [])
  return { fields: data, error }
}

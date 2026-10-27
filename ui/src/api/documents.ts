import type { Document, Field, Filter, Sort } from './types'

export interface DocumentsPage {
  fields: Field[]
  documents: Document[]
  total: number
}

export const PAGE_SIZE = 50

export async function fetchTabularDocuments(
  page: number,
  sort: Sort | null = null,
  filters: Filter[] = [],
): Promise<DocumentsPage> {
  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String((page - 1) * PAGE_SIZE),
  })
  if (sort) {
    params.set('sortField', sort.field)
    params.set('sortDir', sort.dir)
  }
  if (filters.length > 0) {
    params.set('filters', JSON.stringify(filters))
  }
  const res = await fetch(`/api/documents/tabular?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<DocumentsPage>
}

// The full field list, for a document-detail pane not otherwise loading a page of
// documents (e.g. the plot view, which only fetches the plottable fields).
export async function fetchFields(): Promise<Field[]> {
  const res = await fetch('/api/documents/fields')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { fields: Field[] }
  return body.fields
}

export async function fetchDocument(documentId: string): Promise<Document> {
  const res = await fetch(`/api/documents/${encodeURIComponent(documentId)}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<Document>
}

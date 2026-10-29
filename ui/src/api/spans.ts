import type { Filter } from './types'

export interface SpanLabel {
  label: string | null
  spans: number
  documents: number
}

// A span type across documents.
export interface SpanTypeSummary {
  text: string
  label: string | null
  spans: number
  documents: number
  // Distinct span texts among its spans (more than 1 when a norm text brings
  // several surface forms together).
  variants: number
}

export interface SpanSummary {
  // Every span field, and the one summarized (null if there are no span fields).
  fields: string[]
  field: string | null
  labels: SpanLabel[]
  // The most frequent span types, of `totalTypes` matching in all.
  types: SpanTypeSummary[]
  totalTypes: number
}

// An overview of one span field (default: the first): counts per label and the
// most frequent span types. A "span" filter on the field narrows which spans are
// counted (the label counts ignore its labels); other filters, which documents.
export async function fetchSpanSummary(
  field: string | null,
  filters: Filter[] = [],
): Promise<SpanSummary> {
  const params = new URLSearchParams()
  if (field) params.set('field', field)
  if (filters.length > 0) params.set('filters', JSON.stringify(filters))
  const res = await fetch(`/api/spans?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<SpanSummary>
}

export interface Span {
  field: string
  // Character (code point) offsets into the document text, as given in Python.
  start: number
  end: number
  // The text the span covers.
  text: string
  normText: string | null
  label: string | null
  score: number | null
}

// Every span on one document, across all span fields, in text order. "span"
// filters in `filters` prune their field's spans.
export async function fetchDocumentSpans(
  documentId: string,
  filters: Filter[] = [],
): Promise<Span[]> {
  const params = new URLSearchParams()
  if (filters.length > 0) params.set('filters', JSON.stringify(filters))
  const res = await fetch(
    `/api/documents/${encodeURIComponent(documentId)}/spans?${params}`,
  )
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { spans: Span[] }
  return body.spans
}

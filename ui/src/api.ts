export interface Field {
  name: string
  type:
    | 'label'
    | 'score'
    | 'temporal_year'
    | 'temporal_date'
    | 'temporal_datetime'
    | 'text'
    | 'point_2d'
    | 'span'
  // Filter metadata: distinct values for label fields (an "in" filter's
  // candidates), or the min/max bound for score/temporal fields (a "range"
  // filter's domain). Temporal bounds are ISO date/datetime strings. For span
  // fields: their distinct labels (null for unlabelled spans) and score bounds.
  values?: (string | number | null)[] | null
  min?: number | string | null
  max?: number | string | null
  // Label fields only: what each value means (arbitrary JSON per value).
  definitions?: Record<string, unknown> | null
}

export type FilterOp = 'in' | 'range' | 'span'

// A "span" filter matches documents with at least one span in the span field
// `field` with a label among `values` (null: unlabelled), a score within
// `min`/`max`, `text` in its span text or norm text, and exactly `typeText` as its
// type text. It also prunes that field's spans everywhere else: counts, badges and
// highlights only include the spans it matches.
export interface FieldFilter {
  field: string
  op: FilterOp
  values?: (string | null)[]
  min?: number | string
  max?: number | string
  text?: string
  typeText?: string
}

// Documents where any of `fields` contains `text` (ignoring case). A field is a
// text field's name, or 'text' for the source text.
export interface SearchFilter {
  op: 'search'
  text: string
  fields: string[]
}

export type Filter = FieldFilter | SearchFilter

// One span type in a document: the spans sharing a type text (norm text, else
// span text) and label, and how many there are.
export interface SpanTypeCount {
  text: string
  label: string | null
  count: number
}

export type FieldValue =
  string | number | [number, number] | SpanTypeCount[] | null

export interface Document {
  id: string
  text: string
  values: Record<string, FieldValue>
}

export interface DocumentsPage {
  fields: Field[]
  documents: Document[]
  total: number
}

export const PAGE_SIZE = 50

export type SortDir = 'asc' | 'desc'

export interface Sort {
  field: string
  dir: SortDir
}

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

export interface ScatterPoint {
  documentId: string
  x: number
  y: number
  text: string
  group: string | null
}

export interface ScatterData {
  fields: Field[]
  points: ScatterPoint[]
}

export type ScatterQuery = (
  { field: string } | { xField: string; yField: string } | Record<string, never>
) & { colorField?: string; filters?: Filter[] }

export async function fetchScatter(query: ScatterQuery): Promise<ScatterData> {
  const { filters, ...rest } = query
  const entries = Object.entries(rest).filter(
    ([, value]) => value !== undefined,
  )
  const params = new URLSearchParams(
    Object.fromEntries(entries) as Record<string, string>,
  )
  if (filters && filters.length > 0) {
    params.set('filters', JSON.stringify(filters))
  }
  const res = await fetch(`/api/documents/scatter?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<ScatterData>
}

export interface StripPoint {
  documentId: string
  x: number
  text: string
  row: string | null
  color: string | null
}

export interface StripData {
  points: StripPoint[]
}

export interface StripQuery {
  xField: string
  rowField: string
  colorField?: string
  filters?: Filter[]
}

// A strip plot's points: one per document along a score field (`x`), split by a
// label field (`row`), optionally colored by another (`color`).
export async function fetchStrip(query: StripQuery): Promise<StripData> {
  const { filters, ...rest } = query
  const entries = Object.entries(rest).filter(
    ([, value]) => value !== undefined,
  )
  const params = new URLSearchParams(
    Object.fromEntries(entries) as Record<string, string>,
  )
  if (filters && filters.length > 0) {
    params.set('filters', JSON.stringify(filters))
  }
  const res = await fetch(`/api/documents/strip?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<StripData>
}

export interface CrosstabCell {
  row: string | null
  col: string | null
  count: number
}

// Document counts per value pair of two label fields (a confusion matrix).
export async function fetchCrosstab(
  rowField: string,
  colField: string,
): Promise<CrosstabCell[]> {
  const params = new URLSearchParams({ rowField, colField })
  const res = await fetch(`/api/documents/crosstab?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { cells: CrosstabCell[] }
  return body.cells
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

export async function fetchNote(documentId: string): Promise<string> {
  const res = await fetch(
    `/api/documents/${encodeURIComponent(documentId)}/note`,
  )
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { text: string }
  return body.text
}

export async function saveNote(
  documentId: string,
  text: string,
): Promise<void> {
  const res = await fetch(
    `/api/documents/${encodeURIComponent(documentId)}/note`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    },
  )
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
}

export interface NotesFileStatus {
  // Absolute path notes are saved to, or null if none is chosen yet (notes can't
  // be written until one is).
  path: string | null
  suggestedPath: string
  // Set right after choosing a file: what loading the notes already in it found.
  load?: { loaded: number; messages: string[] } | null
}

export async function fetchNotesFile(): Promise<NotesFileStatus> {
  const res = await fetch('/api/notes/file')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<NotesFileStatus>
}

// Choose the file to save notes to, loading any notes already in it.
export async function setNotesFile(path: string): Promise<NotesFileStatus> {
  const res = await fetch('/api/notes/file', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as {
      detail?: string
    } | null
    throw new Error(body?.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<NotesFileStatus>
}

export interface Field {
  name: string
  type:
    | 'label'
    | 'score'
    | 'group'
    | 'temporal_year'
    | 'temporal_date'
    | 'temporal_datetime'
    | 'text'
    | 'point_2d'
  // Filter metadata: distinct values for label/group fields (an "in" filter's
  // candidates), or the min/max bound for score/temporal fields (a "range"
  // filter's domain). Temporal bounds are ISO date/datetime strings.
  values?: (string | number)[] | null
  min?: number | string | null
  max?: number | string | null
}

export type FilterOp = 'in' | 'range' | 'contains'

export interface FieldFilter {
  field: string
  op: FilterOp
  values?: string[]
  min?: number | string
  max?: number | string
  text?: string
}

export type FieldValue = string | number | [number, number] | null

export interface Document {
  id: string
  text: string
  values: Record<string, FieldValue>
  note: string
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
  filters: FieldFilter[] = [],
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
) & { colorField?: string; filters?: FieldFilter[] }

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
  filters?: FieldFilter[]
}

// A strip plot's points: one per document along a score field (`x`), split by a
// label/group field (`row`), optionally colored by another (`color`).
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

// Document counts per value pair of two label/group fields (a confusion matrix).
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

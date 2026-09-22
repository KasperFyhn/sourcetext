export interface Field {
  name: string
  type: 'label' | 'score' | 'group' | 'temporal' | 'free_text' | 'point_2d'
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

export async function fetchTabularDocuments(
  page: number,
): Promise<DocumentsPage> {
  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String((page - 1) * PAGE_SIZE),
  })
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
) & { colorField?: string }

export async function fetchScatter(query: ScatterQuery): Promise<ScatterData> {
  const entries = Object.entries(query).filter(
    ([, value]) => value !== undefined,
  )
  const params = new URLSearchParams(
    Object.fromEntries(entries) as Record<string, string>,
  )
  const res = await fetch(`/api/documents/scatter?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<ScatterData>
}

// The full field list, for a document-detail pane not otherwise loading a page of
// documents (e.g. the scatter view, which only fetches point_2d/score fields).
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

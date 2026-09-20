export interface Field {
  name: string
  type: 'label' | 'score' | 'group' | 'temporal' | 'free_text'
}

export type FieldValue = string | number | null

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

export async function fetchDocuments(page: number): Promise<DocumentsPage> {
  const params = new URLSearchParams({
    limit: String(PAGE_SIZE),
    offset: String((page - 1) * PAGE_SIZE),
  })
  const res = await fetch(`/api/documents?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<DocumentsPage>
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

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

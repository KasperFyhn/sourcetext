import { useState } from 'react'

import { saveNote } from '../api'
import type { Document } from '../api'

// Unsaved/edited notes for the current selection, falling back to the note loaded
// from the server. Shared between TabularView and ScatterView, which both let the
// user select a document and edit its note the same way.
export function useDocumentNotes(
  selected: Document | null,
  setError: (message: string | null) => void,
) {
  const [notes, setNotes] = useState<Record<string, string>>({})

  const currentNotes = selected ? (notes[selected.id] ?? selected.note) : ''

  const handleNotesChange = (value: string) => {
    if (selected) setNotes((prev) => ({ ...prev, [selected.id]: value }))
  }

  const handleNotesSave = () => {
    if (!selected || notes[selected.id] === undefined) return
    saveNote(selected.id, notes[selected.id])
      .then(() => setError(null))
      .catch((err: Error) => setError(`Could not save note: ${err.message}`))
  }

  return { currentNotes, handleNotesChange, handleNotesSave }
}

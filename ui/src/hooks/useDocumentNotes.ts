import { useState } from 'react'

import { saveNote } from '../api'
import type { Document } from '../api'

// Unsaved/edited notes for the current document, falling back to the note loaded
// from the server, plus the error from the last failed save of this document, if any.
export function useDocumentNotes(document: Document | null) {
  const [notes, setNotes] = useState<Record<string, string>>({})
  // Keyed by document, so a failed save isn't shown on another document.
  const [errors, setErrors] = useState<Record<string, string | null>>({})

  const currentNotes = document ? (notes[document.id] ?? document.note) : ''
  const error = document ? (errors[document.id] ?? null) : null

  const handleNotesChange = (value: string) => {
    if (document) setNotes((prev) => ({ ...prev, [document.id]: value }))
  }

  const handleNotesSave = () => {
    if (!document || notes[document.id] === undefined) return
    const { id } = document
    const setError = (message: string | null) =>
      setErrors((prev) => ({ ...prev, [id]: message }))
    saveNote(id, notes[id])
      .then(() => setError(null))
      .catch((err: Error) => setError(`Could not save note: ${err.message}`))
  }

  return { currentNotes, handleNotesChange, handleNotesSave, error }
}

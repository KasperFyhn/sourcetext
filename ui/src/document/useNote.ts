import { useEffect, useState } from 'react'

import { fetchNote, saveNote } from '../api/notes'

// The note on one document, editable: `text` is what's typed, `save` writes it if
// it changed. `path` is the notes file (null: none chosen, so nothing is saved).
export function useNote(documentId: string, path: string | null) {
  const [text, setText] = useState('')
  // The text as last loaded or saved, to tell whether there's anything to save.
  const [savedText, setSavedText] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Reloaded when the notes file changes too: choosing an existing file can bring
  // in a note for this document.
  useEffect(() => {
    let stale = false
    fetchNote(documentId)
      .then((note) => {
        if (stale) return
        setText(note)
        setSavedText(note)
        setError(null)
      })
      .catch(
        (err: Error) =>
          !stale && setError(`Could not load note: ${err.message}`),
      )
    return () => {
      stale = true
    }
  }, [documentId, path])

  const save = () => {
    if (!path || text === savedText) return
    const saving = text
    saveNote(documentId, saving)
      .then(() => {
        setSavedText(saving)
        setError(null)
      })
      .catch((err: Error) => setError(`Could not save note: ${err.message}`))
  }

  return { text, setText, save, error }
}

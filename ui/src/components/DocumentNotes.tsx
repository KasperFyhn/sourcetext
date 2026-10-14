import { Group, Text, Textarea, Tooltip, UnstyledButton } from '@mantine/core'
import { useEffect, useState } from 'react'

import { fetchNote, saveNote } from '../api'
import { useNotesFile } from '../contexts/NotesFileContext'

interface Props {
  documentId: string
}

// The note on one document: loads it, saves it on blur, and shows where notes
// are saved. Writing is disabled until a notes file is chosen.
export function DocumentNotes({ documentId }: Props) {
  const { status, openDialog } = useNotesFile()
  const path = status?.path ?? null
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

  const handleSave = () => {
    if (!path || text === savedText) return
    const saving = text
    saveNote(documentId, saving)
      .then(() => {
        setSavedText(saving)
        setError(null)
      })
      .catch((err: Error) => setError(`Could not save note: ${err.message}`))
  }

  return (
    <Textarea
      label={
        <Group gap="xs">
          Notes
          <Tooltip
            label={
              path
                ? `Saved to ${path}. Click to change.`
                : 'Notes are saved to a file. Click to choose one.'
            }
          >
            <UnstyledButton onClick={openDialog}>
              <Text size="xs" c="dimmed">
                {path
                  ? `saved to ${path.split(/[\\/]/).pop()}`
                  : 'Select notes file ...'}
              </Text>
            </UnstyledButton>
          </Tooltip>
        </Group>
      }
      placeholder={
        path
          ? 'Write your interpretation of this document...'
          : 'Select a notes file to start taking notes.'
      }
      disabled={!path}
      error={error}
      autosize
      minRows={4}
      value={text}
      onChange={(event) => setText(event.currentTarget.value)}
      onBlur={handleSave}
    />
  )
}

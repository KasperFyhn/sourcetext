import { Alert, Box, Flex, Loader, Pagination, Stack } from '@mantine/core'
import { useEffect, useState } from 'react'

import { fetchDocuments, PAGE_SIZE, saveNote } from './api'
import type { Document, DocumentsPage } from './api'
import { DocumentTable } from './components/DocumentTable'
import { DocumentView } from './components/DocumentView'

function App() {
  const [page, setPage] = useState(1)
  const [data, setData] = useState<DocumentsPage | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  // Unsaved/edited notes by document id; falls back to the note loaded from the server.
  const [notes, setNotes] = useState<Record<string, string>>({})

  useEffect(() => {
    let stale = false
    fetchDocuments(page)
      .then((result) => {
        if (stale) return
        setData(result)
        setError(null)
      })
      .catch((err: Error) => !stale && setError(err.message))
    return () => {
      stale = true
    }
  }, [page])

  const fields = data?.fields ?? []
  const currentNotes = selected ? (notes[selected.id] ?? selected.note) : ''

  const handleNotesSave = () => {
    if (!selected || notes[selected.id] === undefined) return
    saveNote(selected.id, notes[selected.id])
      .then(() => setError(null))
      .catch((err: Error) => setError(`Could not save note: ${err.message}`))
  }

  return (
    <Flex h="100vh">
      <Box flex={2} p="md" style={{ overflowY: 'auto' }}>
        <DocumentView
          fields={fields}
          document={selected}
          notes={currentNotes}
          onNotesSave={handleNotesSave}
          onNotesChange={(value) =>
            selected && setNotes((prev) => ({ ...prev, [selected.id]: value }))
          }
        />
      </Box>
      <Box
        flex={2}
        p="md"
        style={{
          overflow: 'auto',
          borderLeft: '1px solid var(--mantine-color-default-border)',
        }}
      >
        <Stack>
          {error && (
            <Alert color="red" title="Something went wrong">
              {error}
            </Alert>
          )}
          {!error && !data && <Loader />}
          {data && (
            <>
              <DocumentTable
                fields={fields}
                documents={data.documents}
                selectedId={selected?.id ?? null}
                onSelect={setSelected}
              />
              <Pagination
                value={page}
                onChange={setPage}
                total={Math.max(1, Math.ceil(data.total / PAGE_SIZE))}
              />
            </>
          )}
        </Stack>
      </Box>
    </Flex>
  )
}

export default App

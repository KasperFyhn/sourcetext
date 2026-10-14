import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { fetchNotesFile, setNotesFile } from '../api'
import type { NotesFileStatus } from '../api'
import { NotesFileDialog } from '../components/NotesFileDialog'

interface NotesFileContextValue {
  status: NotesFileStatus | null
  openDialog: () => void
}

// null outside NotesFileProvider, so that misuse fails loudly instead of
// silently leaving notes disabled.
const NotesFileContext = createContext<NotesFileContextValue | null>(null)

export function useNotesFile() {
  const context = useContext(NotesFileContext)
  if (context === null)
    throw new Error('useNotesFile must be used inside NotesFileProvider')
  return context
}

// Holds where notes are saved, shared by all views, and the dialog for choosing
// it. Notes can't be written until a file is chosen, so they're never kept only
// in memory.
export function NotesFileProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<NotesFileStatus | null>(null)
  const [opened, setOpened] = useState(false)
  // Bumped on every open, so the dialog starts from a fresh form each time.
  const [dialogKey, setDialogKey] = useState(0)

  useEffect(() => {
    fetchNotesFile()
      .then(setStatus)
      .catch(() => {})
  }, [])

  const openDialog = () => {
    setDialogKey((key) => key + 1)
    setOpened(true)
  }

  const choose = async (path: string) => {
    const result = await setNotesFile(path)
    setStatus(result)
    return result
  }

  return (
    <NotesFileContext.Provider value={{ status, openDialog }}>
      {children}
      <NotesFileDialog
        key={dialogKey}
        opened={opened}
        status={status}
        onChoose={choose}
        onClose={() => setOpened(false)}
      />
    </NotesFileContext.Provider>
  )
}

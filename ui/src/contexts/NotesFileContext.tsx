import {
  Alert,
  Button,
  Code,
  Group,
  List,
  Modal,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'

import { fetchNotesFile, setNotesFile } from '../api'
import type { NotesFileStatus } from '../api'

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

interface NotesFileDialogProps {
  opened: boolean
  status: NotesFileStatus | null
  // Chooses the file; rejects with a message to show if it can't be used.
  onChoose: (path: string) => Promise<NotesFileStatus>
  onClose: () => void
}

// The dialog for choosing the notes file; only ever opened by the provider.
function NotesFileDialog({
  opened,
  status,
  onChoose,
  onClose,
}: NotesFileDialogProps) {
  const [path, setPath] = useState(status?.path ?? status?.suggestedPath ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  // What loading an existing file found; shown before closing the dialog.
  const [loadResult, setLoadResult] = useState<NotesFileStatus['load']>(null)

  const choose = () => {
    setSaving(true)
    onChoose(path)
      .then((result) => {
        setError(null)
        if (result.load && (result.load.loaded || result.load.messages.length))
          setLoadResult(result.load)
        else onClose()
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setSaving(false))
  }

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title="Choose a notes file"
      size="lg"
    >
      {loadResult ? (
        <Stack>
          <Text>
            Notes are now saved to <Code>{status?.path}</Code>.
            {loadResult.loaded > 0 &&
              ` Loaded ${loadResult.loaded} note(s) already in the file.`}
          </Text>
          {loadResult.messages.length > 0 && (
            <List size="sm">
              {loadResult.messages.map((message) => (
                <List.Item key={message}>{message}</List.Item>
              ))}
            </List>
          )}
          <Group justify="flex-end">
            <Button onClick={onClose}>Done</Button>
          </Group>
        </Stack>
      ) : (
        <Stack>
          <Text size="sm">
            {status?.path
              ? 'Notes are saved to the file below. Choose another file to save them there instead.'
              : 'Notes are saved to a JSONL file, so they are kept between sessions. Choose a new file, or the file you saved notes to before to continue with them.'}
          </Text>
          <TextInput
            label="File"
            description="Relative paths are relative to the working directory of your Python session."
            value={path}
            onChange={(event) => setPath(event.currentTarget.value)}
          />
          <Text size="sm" c="dimmed">
            To load the notes again next time, pass{' '}
            <Code>notes_file=&quot;{path || '…'}&quot;</Code> to{' '}
            <Code>SourceText</Code>.
          </Text>
          {error && (
            <Alert color="red" title="Could not use this file">
              {error}
            </Alert>
          )}
          <Group justify="flex-end">
            <Button loading={saving} disabled={!path.trim()} onClick={choose}>
              Save notes to this file
            </Button>
          </Group>
        </Stack>
      )}
    </Modal>
  )
}

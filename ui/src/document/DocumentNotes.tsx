import { Group, Text, Textarea, Tooltip, UnstyledButton } from '@mantine/core'
import { useNotesFile } from '../contexts/NotesFileContext'
import { useNote } from './useNote'

interface Props {
  documentId: string
}

// The note on one document: loads it, saves it on blur, and shows where notes
// are saved. Writing is disabled until a notes file is chosen.
export function DocumentNotes({ documentId }: Props) {
  const { status, openDialog } = useNotesFile()
  const path = status?.path ?? null
  const { text, setText, save, error } = useNote(documentId, path)

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
      onBlur={save}
    />
  )
}

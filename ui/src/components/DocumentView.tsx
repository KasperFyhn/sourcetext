import {
  Box,
  Flex,
  Group,
  Stack,
  Text,
  Textarea,
  Title,
  Tooltip,
  UnstyledButton,
} from '@mantine/core'

import type { Document, Field } from '../api'
import { useNotesFile } from '../contexts/NotesFileContext'
import { useDocumentNotes } from '../hooks/useDocumentNotes'
import { FieldValueView } from './FieldValueView'

interface Props {
  fields: Field[]
  document: Document | null
}

export function DocumentView({ fields, document }: Props) {
  const { status, openDialog } = useNotesFile()
  const { currentNotes, handleNotesChange, handleNotesSave, error } =
    useDocumentNotes(document)

  return (
    <Box
      flex={2}
      p="md"
      style={{
        overflowY: 'auto',
        borderLeft: '1px solid var(--mantine-color-default-border)',
      }}
    >
      {!document ? (
        <Text c="dimmed">
          Select a document in the navigation pane to view it.
        </Text>
      ) : (
        <Stack>
          <Title order={2}>Document {document.id}</Title>
          <Group align="stretch">
            {fields.map((field) => (
              <Stack key={field.name} gap={2}>
                <Text size="xs" c="dimmed">
                  {field.name}
                </Text>
                <Flex align="center" flex={1}>
                  <FieldValueView
                    field={field}
                    value={document.values[field.name]}
                  />
                </Flex>
              </Stack>
            ))}
          </Group>
          <Text style={{ whiteSpace: 'pre-wrap' }}>{document.text}</Text>
          <Textarea
            label={
              <Group gap="xs">
                Notes
                <Tooltip
                  label={
                    status?.path
                      ? `Saved to ${status.path}. Click to change.`
                      : 'Notes are saved to a file. Click to choose one.'
                  }
                >
                  <UnstyledButton onClick={openDialog}>
                    <Text size="xs" c="dimmed">
                      {status?.path
                        ? `saved to ${status.path.split(/[\\/]/).pop()}`
                        : 'Select notes file ...'}
                    </Text>
                  </UnstyledButton>
                </Tooltip>
              </Group>
            }
            placeholder={
              status?.path
                ? 'Write your interpretation of this document...'
                : 'Select a notes file to start taking notes.'
            }
            disabled={!status?.path}
            error={error}
            autosize
            minRows={4}
            value={currentNotes}
            onChange={(event) => handleNotesChange(event.currentTarget.value)}
            onBlur={handleNotesSave}
          />
        </Stack>
      )}
    </Box>
  )
}

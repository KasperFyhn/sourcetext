import {
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
import { FieldValueView } from './FieldValueView'

interface Props {
  fields: Field[]
  document: Document | null
  notes: string
  onNotesChange: (notes: string) => void
  onNotesSave: () => void
}

export function DocumentView({
  fields,
  document,
  notes,
  onNotesChange,
  onNotesSave,
}: Props) {
  const { status, openDialog } = useNotesFile()

  if (!document)
    return (
      <Text c="dimmed">
        Select a document in the navigation pane to view it.
      </Text>
    )

  return (
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
        autosize
        minRows={4}
        value={notes}
        onChange={(event) => onNotesChange(event.currentTarget.value)}
        onBlur={onNotesSave}
      />
    </Stack>
  )
}

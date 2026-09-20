import { Group, Stack, Text, Textarea, Title } from '@mantine/core'

import type { Document, Field } from '../api'
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
  if (!document)
    return <Text c="dimmed">Select a document in the table to view it.</Text>

  return (
    <Stack>
      <Title order={2}>Document {document.id}</Title>
      <Group>
        {fields.map((field) => (
          <Stack key={field.name} gap={2}>
            <Text size="xs" c="dimmed">
              {field.name}
            </Text>
            <FieldValueView field={field} value={document.values[field.name]} />
          </Stack>
        ))}
      </Group>
      <Text style={{ whiteSpace: 'pre-wrap' }}>{document.text}</Text>
      <Textarea
        label="Notes"
        placeholder="Write your interpretation of this document..."
        autosize
        minRows={4}
        value={notes}
        onChange={(event) => onNotesChange(event.currentTarget.value)}
        onBlur={onNotesSave}
      />
    </Stack>
  )
}

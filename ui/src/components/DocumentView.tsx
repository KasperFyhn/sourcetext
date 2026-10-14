import { Box, Flex, Group, Stack, Text, Title } from '@mantine/core'

import type { Document, Field } from '../api'
import { DocumentNotes } from './DocumentNotes'
import { FieldValueView } from './FieldValueView'

interface Props {
  fields: Field[]
  document: Document | null
}

export function DocumentView({ fields, document }: Props) {
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
          <DocumentNotes key={document.id} documentId={document.id} />
        </Stack>
      )}
    </Box>
  )
}

import { Box, Flex, Group, Mark, Stack, Text, Title } from '@mantine/core'
import type { ReactNode } from 'react'

import type { Document, Field } from '../api'
import { DocumentNotes } from './DocumentNotes'
import { FieldValueView } from './FieldValueView'

interface Props {
  fields: Field[]
  document: Document | null
  // Character ranges of the text to mark, e.g. the spans a view navigated by.
  highlights?: { start: number; end: number }[]
}

// The text with `highlights` marked. Offsets count code points (as Python does),
// not JS's UTF-16 units, hence `Array.from`. Overlapping ranges are merged.
function highlightText(
  text: string,
  highlights: { start: number; end: number }[],
): ReactNode {
  if (highlights.length === 0) return text
  const chars = Array.from(text)
  const ranges = [...highlights].sort((a, b) => a.start - b.start)
  const parts: ReactNode[] = []
  let pos = 0
  for (const { start, end } of ranges) {
    if (end <= pos) continue
    const from = Math.max(start, pos)
    parts.push(chars.slice(pos, from).join(''))
    parts.push(<Mark key={from}>{chars.slice(from, end).join('')}</Mark>)
    pos = end
  }
  parts.push(chars.slice(pos).join(''))
  return parts
}

export function DocumentView({ fields, document, highlights = [] }: Props) {
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
          <Text style={{ whiteSpace: 'pre-wrap' }}>
            {highlightText(document.text, highlights)}
          </Text>
          <DocumentNotes key={document.id} documentId={document.id} />
        </Stack>
      )}
    </Box>
  )
}

import { Flex, Group, Mark, Stack, Text, Title } from '@mantine/core'
import { useMemo, useState } from 'react'

import type { Document, Field, Filter } from '../api/types'
import { FieldValueView } from '../fields/FieldValueView'
import { SpanBadge } from '../fields/span/SpanBadge'
import {
  aggregateSpanTypes,
  spanTypeKey,
  typeKey,
} from '../fields/span/spanTypes'
import type { SpanTypeKey } from '../fields/span/spanTypes'
import { DocumentNotes } from './DocumentNotes'
import { highlightSegments } from './highlight'
import { useDocumentSpans } from './useDocumentSpans'

interface DetailProps {
  fields: Field[]
  document: Document
  filters: Filter[]
  highlightType: SpanTypeKey | null
}

// Keyed by document, so the span types highlighted start over for each one.
export function DocumentDetail({
  fields,
  document,
  filters,
  highlightType,
}: DetailProps) {
  const spans = useDocumentSpans(document.id, filters)
  const initialKey = highlightType ? typeKey(highlightType) : null
  const [active, setActive] = useState<Set<string>>(
    new Set(initialKey ? [initialKey] : []),
  )

  // A newly navigated-by type replaces whatever was highlighted (adjusted during
  // render rather than in an effect, as React recommends).
  const [prevInitialKey, setPrevInitialKey] = useState(initialKey)
  if (initialKey !== prevInitialKey) {
    setPrevInitialKey(initialKey)
    setActive(new Set(initialKey ? [initialKey] : []))
  }

  const spanFields = fields.filter((f) => f.type === 'span')
  const otherFields = fields.filter((f) => f.type !== 'span')
  const typesByField = useMemo(() => aggregateSpanTypes(spans), [spans])
  const highlights = spans.filter((s) => active.has(spanTypeKey(s)))

  const toggle = (key: string) =>
    setActive((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })

  return (
    <Flex gap="lg" align="flex-start">
      <Stack flex={1} miw={0}>
        <Title order={2}>Document {document.id}</Title>
        <Group align="stretch">
          {otherFields.map((field) => (
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
          {highlightSegments(document.text, highlights).map((segment) =>
            segment.marked ? (
              <Mark key={segment.start}>{segment.text}</Mark>
            ) : (
              segment.text
            ),
          )}
        </Text>
        <DocumentNotes documentId={document.id} />
      </Stack>
      {spanFields.length > 0 && (
        <Stack gap="sm" w={240} style={{ flexShrink: 0 }}>
          {spanFields.map((field) => {
            const types = typesByField.get(field.name) ?? []
            return (
              <Stack key={field.name} gap={4}>
                <Text size="xs" c="dimmed">
                  {field.name}
                </Text>
                {types.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    –
                  </Text>
                ) : (
                  <Group gap={4}>
                    {types.map((type) => (
                      <SpanBadge
                        key={type.key}
                        text={type.text}
                        label={type.label}
                        count={type.count}
                        active={active.has(type.key)}
                        onClick={() => toggle(type.key)}
                      />
                    ))}
                  </Group>
                )}
              </Stack>
            )
          })}
          <Text size="xs" c="dimmed">
            Click a span to highlight it in the text.
          </Text>
        </Stack>
      )}
    </Flex>
  )
}

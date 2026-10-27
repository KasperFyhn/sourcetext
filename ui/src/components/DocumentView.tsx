import { Box, Flex, Group, Mark, Stack, Text, Title } from '@mantine/core'
import type { ReactNode } from 'react'
import { useEffect, useMemo, useState } from 'react'

import { fetchDocumentSpans } from '../api/spans'
import type { Span } from '../api/spans'
import type { Document, Field, Filter } from '../api/types'
import { DocumentNotes } from './DocumentNotes'
import { FieldValueView } from './FieldValueView'
import { SpanBadge } from './SpanBadge'

// One span type: the spans in a span field sharing a type text and label.
export interface SpanTypeKey {
  field: string
  text: string
  label: string | null
}

interface Props {
  fields: Field[]
  document: Document | null
  // The view's filters: "span" filters among them prune the spans listed and
  // highlighted to the ones they match.
  filters?: Filter[]
  // A span type to highlight from the start, e.g. the one a view navigated by.
  highlightType?: SpanTypeKey | null
}

function typeKey({ field, text, label }: SpanTypeKey): string {
  return JSON.stringify([field, label, text])
}

function spanTypeKey(span: Span): string {
  return typeKey({
    field: span.field,
    text: span.normText ?? span.text,
    label: span.label,
  })
}

interface SpanTypeCount extends SpanTypeKey {
  key: string
  count: number
}

// A document's span types per span field, most frequent first.
function aggregateSpanTypes(spans: Span[]): Map<string, SpanTypeCount[]> {
  const byKey = new Map<string, SpanTypeCount>()
  for (const span of spans) {
    const key = spanTypeKey(span)
    const existing = byKey.get(key)
    if (existing) existing.count += 1
    else
      byKey.set(key, {
        key,
        field: span.field,
        text: span.normText ?? span.text,
        label: span.label,
        count: 1,
      })
  }
  const byField = new Map<string, SpanTypeCount[]>()
  const sorted = [...byKey.values()].sort(
    (a, b) => b.count - a.count || a.text.localeCompare(b.text),
  )
  for (const type of sorted) {
    byField.set(type.field, [...(byField.get(type.field) ?? []), type])
  }
  return byField
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

export function DocumentView({
  fields,
  document,
  filters = [],
  highlightType = null,
}: Props) {
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
        <DocumentDetail
          key={document.id}
          fields={fields}
          document={document}
          filters={filters}
          highlightType={highlightType}
        />
      )}
    </Box>
  )
}

interface DetailProps {
  fields: Field[]
  document: Document
  filters: Filter[]
  highlightType: SpanTypeKey | null
}

// Keyed by document, so the span types highlighted start over for each one.
function DocumentDetail({
  fields,
  document,
  filters,
  highlightType,
}: DetailProps) {
  const [spans, setSpans] = useState<Span[]>([])
  const initialKey = highlightType ? typeKey(highlightType) : null
  const [active, setActive] = useState<Set<string>>(
    new Set(initialKey ? [initialKey] : []),
  )

  // Only "span" filters prune the spans, so other filter changes don't refetch.
  const spanFilters = JSON.stringify(filters.filter((f) => f.op === 'span'))
  useEffect(() => {
    let stale = false
    fetchDocumentSpans(document.id, JSON.parse(spanFilters) as Filter[])
      .then((result) => !stale && setSpans(result))
      .catch(() => !stale && setSpans([]))
    return () => {
      stale = true
    }
  }, [document.id, spanFilters])

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
          {highlightText(document.text, highlights)}
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

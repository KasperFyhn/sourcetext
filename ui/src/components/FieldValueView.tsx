import { Badge, Group, Text } from '@mantine/core'

import type { Field, FieldValue, SpanTypeCount } from '../api'
import { LabelDefinitionInfo } from './LabelDefinition'
import { SpanBadge } from './SpanBadge'

// How many of a document's span types a span field's value shows, most frequent
// first, before folding the rest into "+N".
const MAX_SPAN_BADGES = 3

export function FieldValueView({
  field,
  value,
}: {
  field: Field
  value: FieldValue | undefined
}) {
  if (value === undefined || value === null) return <Text c="dimmed">–</Text>
  if (field.type === 'span' && Array.isArray(value)) {
    const types = value as SpanTypeCount[]
    const rest = types.length - MAX_SPAN_BADGES
    return (
      <Group gap={4} maw={420}>
        {types.slice(0, MAX_SPAN_BADGES).map((t) => (
          <SpanBadge
            key={`${t.label}\u0000${t.text}`}
            text={t.text}
            label={t.label}
            count={t.count}
          />
        ))}
        {rest > 0 && (
          <Text size="xs" c="dimmed">
            +{rest}
          </Text>
        )}
      </Group>
    )
  }

  if (field.type === 'point_2d' && Array.isArray(value)) {
    const [x, y] = value as [number, number]
    return (
      <Text>
        ({x.toFixed(2)}, {y.toFixed(2)})
      </Text>
    )
  }
  if (Array.isArray(value)) return <Text c="dimmed">–</Text>
  if (field.type === 'label')
    return (
      <Badge
        variant="light"
        rightSection={
          <LabelDefinitionInfo definitions={field.definitions} value={value} />
        }
      >
        {value}
      </Badge>
    )
  if (typeof value === 'number' && !Number.isInteger(value))
    return <Text>{value.toFixed(3)}</Text>
  return <Text truncate>{value}</Text>
}

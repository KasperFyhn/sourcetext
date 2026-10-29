import { Group, Text } from '@mantine/core'

import type { SpanTypeCount } from '../../api/types'
import { SpanBadge } from './SpanBadge'

// How many of a document's span types a span field's value shows, most frequent
// first, before folding the rest into "+N".
const MAX_SPAN_BADGES = 3

export function SpanValue({ types }: { types: SpanTypeCount[] }) {
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

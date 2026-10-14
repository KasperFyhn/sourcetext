import { Badge, Text } from '@mantine/core'

interface Props {
  // The type text: the norm text, else the span text.
  text: string
  label: string | null
  count?: number
  // Filled rather than light, e.g. while its spans are highlighted.
  active?: boolean
  onClick?: () => void
}

// One span type outside the text: its type text, its label (if any), and how many
// of its spans there are when more than one.
export function SpanBadge({ text, label, count, active, onClick }: Props) {
  return (
    <Badge
      variant={active ? 'filled' : 'light'}
      tt="none"
      maw={260}
      onClick={onClick}
      style={onClick ? { cursor: 'pointer' } : undefined}
      title={label ? `${text} (${label})` : text}
    >
      {text}
      {label && (
        <Text span size="xs" fw={500} opacity={0.7} ml={6}>
          {label}
        </Text>
      )}
      {count !== undefined && count > 1 && (
        <Text span size="xs" fw={500} opacity={0.7} ml={6}>
          ×{count}
        </Text>
      )}
    </Badge>
  )
}

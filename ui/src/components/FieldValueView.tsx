import { Badge, Text } from '@mantine/core'

import type { Field, FieldValue } from '../api'

export function FieldValueView({
  field,
  value,
}: {
  field: Field
  value: FieldValue | undefined
}) {
  if (value === undefined || value === null) return <Text c="dimmed">–</Text>
  if (field.type === 'label' || field.type === 'group')
    return <Badge variant="light">{value}</Badge>
  if (typeof value === 'number' && !Number.isInteger(value))
    return <Text>{value.toFixed(3)}</Text>
  return <Text truncate>{value}</Text>
}

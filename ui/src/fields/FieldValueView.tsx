import { Text } from '@mantine/core'

import type { Field, FieldValue, SpanTypeCount } from '../api/types'
import { LabelValue } from './label/LabelValue'
import { Point2DValue } from './point2d/Point2DValue'
import { SpanValue } from './span/SpanValue'

// A field's value in a document, shown per field type.
export function FieldValueView({
  field,
  value,
}: {
  field: Field
  value: FieldValue | undefined
}) {
  if (value === undefined || value === null) return <Text c="dimmed">–</Text>
  if (field.type === 'span' && Array.isArray(value))
    return <SpanValue types={value as SpanTypeCount[]} />
  if (field.type === 'point_2d' && Array.isArray(value))
    return <Point2DValue point={value as [number, number]} />
  if (Array.isArray(value)) return <Text c="dimmed">–</Text>
  if (field.type === 'label') return <LabelValue field={field} value={value} />
  if (typeof value === 'number' && !Number.isInteger(value))
    return <Text>{value.toFixed(3)}</Text>
  return <Text truncate>{value}</Text>
}

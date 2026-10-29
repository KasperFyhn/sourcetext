import { Badge } from '@mantine/core'

import type { Field } from '../../api/types'
import { LabelDefinitionInfo } from './LabelDefinitionInfo'

export function LabelValue({
  field,
  value,
}: {
  field: Field
  value: string | number
}) {
  return (
    <Badge
      variant="light"
      rightSection={
        <LabelDefinitionInfo definitions={field.definitions} value={value} />
      }
      style={{ cursor: 'inherit' }}
    >
      {value}
    </Badge>
  )
}

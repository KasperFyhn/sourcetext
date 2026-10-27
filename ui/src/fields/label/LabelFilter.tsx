import { Chip, Group, Input } from '@mantine/core'

import { setFieldFilter } from '../filters'
import type { ControlProps } from '../filters'
import { LabelDefinitionInfo } from './LabelDefinitionInfo'

export function LabelFilter({ field, current, onChange }: ControlProps) {
  const options = (field.values ?? []).map(String)
  return (
    <Chip.Group
      multiple
      value={(current?.values ?? []).filter((v) => v !== null)}
      onChange={(values) =>
        onChange((prev) =>
          setFieldFilter(
            prev,
            field.name,
            values.length > 0 ? { field: field.name, op: 'in', values } : null,
          ),
        )
      }
    >
      <Input.Wrapper label={field.name}>
        <Group gap={6} mih={36}>
          {options.map((option) => (
            <Chip key={option} value={option} size="xs" variant="outline">
              {option}{' '}
              <LabelDefinitionInfo
                definitions={field.definitions}
                value={option}
              />
            </Chip>
          ))}
        </Group>
      </Input.Wrapper>
    </Chip.Group>
  )
}

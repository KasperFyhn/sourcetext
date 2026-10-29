import { HoverCard, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

import { LabelDefinitionView } from './LabelDefinitionView'
import { definitionOf } from './labelDefinitions'
import type { LabelDefinitions } from './labelDefinitions'

// An info icon that shows a label value's definition on hover; renders nothing if
// the value has none. Placed next to the value, e.g. as a Badge's rightSection.
// With `svg`, it renders as a "ⓘ" <tspan>, for inside an SVG <text> label.
export function LabelDefinitionInfo({
  definitions,
  value,
  svg = false,
}: {
  definitions: LabelDefinitions
  value: unknown
  svg?: boolean
}) {
  const definition = definitionOf(definitions, value)
  if (definition === undefined) return null
  return (
    <HoverCard openDelay={250} width={320} shadow="md" withinPortal>
      <HoverCard.Target>
        {svg ? (
          <tspan dx={4} opacity={0.7} style={{ cursor: 'help' }}>
            ⓘ
          </tspan>
        ) : (
          <IconInfoCircle
            size={13}
            stroke={1.75}
            color="currentColor"
            opacity={0.7}
            style={{ cursor: 'help', flexShrink: 0, verticalAlign: 'middle' }}
          />
        )}
      </HoverCard.Target>
      <HoverCard.Dropdown mah={360} style={{ overflowY: 'auto' }}>
        <Text size="xs" c="dimmed" mb={4}>
          {String(value)}
        </Text>
        <LabelDefinitionView definition={definition} />
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

import { Flex, Paper, Stack, Text } from '@mantine/core'

import { LabelDefinitionInfo } from '../../fields/label/LabelDefinition'
import type { LabelDefinitions } from '../../fields/label/LabelDefinition'
import type { ColorScale } from '../../lib/colors'

// The plot views' color key, overlaid in the top-right corner. Entries whose label
// has a definition get an info icon showing it on hover.
export function ColorLegend({
  legend,
  definitions,
}: {
  legend: ColorScale['legend']
  definitions?: LabelDefinitions
}) {
  return (
    <Paper
      shadow="xs"
      withBorder
      p={6}
      style={{ position: 'absolute', top: 8, right: 8 }}
    >
      <Stack gap={4}>
        {legend.map((entry) => (
          <Flex key={entry.label} align="center" gap={6}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: entry.color,
                flexShrink: 0,
              }}
            />
            <Text size="xs">{entry.label}</Text>
            <LabelDefinitionInfo
              definitions={definitions}
              value={entry.label}
            />
          </Flex>
        ))}
      </Stack>
    </Paper>
  )
}

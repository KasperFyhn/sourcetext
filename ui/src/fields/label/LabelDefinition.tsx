import { Code, HoverCard, Table, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

// A label field's `{value: definition}` map; definitions are arbitrary JSON.
export type LabelDefinitions = Record<string, unknown> | null | undefined

export function definitionOf(
  definitions: LabelDefinitions,
  value: unknown,
): unknown {
  if (value === null || value === undefined) return undefined
  return definitions?.[String(value)]
}

const formatWeight = (weight: number) =>
  Number.isInteger(weight) ? String(weight) : weight.toFixed(3)

// Keyword-style definitions (e.g. a topic's top words with weights), as
// `[word, weight]` pairs or a `{word: weight}` object; null for anything else.
function asWeightedTerms(definition: unknown): [string, number][] | null {
  const entries = Array.isArray(definition)
    ? definition
    : typeof definition === 'object' && definition !== null
      ? Object.entries(definition)
      : null
  if (!entries || entries.length === 0) return null
  const isPair = (entry: unknown) =>
    Array.isArray(entry) &&
    entry.length === 2 &&
    typeof entry[0] === 'string' &&
    typeof entry[1] === 'number'
  return entries.every(isPair) ? (entries as [string, number][]) : null
}

function isStringList(definition: unknown): definition is string[] {
  return (
    Array.isArray(definition) &&
    definition.every((item) => typeof item === 'string')
  )
}

export function LabelDefinitionView({ definition }: { definition: unknown }) {
  if (typeof definition === 'string')
    return (
      <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
        {definition}
      </Text>
    )
  const terms = asWeightedTerms(definition)
  if (terms)
    return (
      <Table withRowBorders={false} verticalSpacing={2} horizontalSpacing={4}>
        <Table.Tbody>
          {terms.map(([term, weight]) => (
            <Table.Tr key={term}>
              <Table.Td>
                <Text size="sm">{term}</Text>
              </Table.Td>
              <Table.Td ta="right">
                <Text size="xs" c="dimmed">
                  {formatWeight(weight)}
                </Text>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    )
  if (isStringList(definition))
    return <Text size="sm">{definition.join(', ')}</Text>
  return (
    <Code block style={{ whiteSpace: 'pre-wrap' }}>
      {JSON.stringify(definition, null, 2)}
    </Code>
  )
}

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

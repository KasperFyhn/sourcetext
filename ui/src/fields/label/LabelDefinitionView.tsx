import { Code, Table, Text } from '@mantine/core'

import { asWeightedTerms, formatWeight, isStringList } from './labelDefinitions'

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

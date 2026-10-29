import { ScrollArea, Table, Text } from '@mantine/core'

import type { SpanTypeSummary } from '../../api/spans'
import { SpanBadge } from '../../fields/span/SpanBadge'

interface SpanTypeTableProps {
  types: SpanTypeSummary[]
  selected: SpanTypeSummary | null
  onSelect: (type: SpanTypeSummary) => void
}

export function SpanTypeTable({
  types,
  selected,
  onSelect,
}: SpanTypeTableProps) {
  if (types.length === 0) {
    return (
      <Text size="sm" c="dimmed">
        No matching spans.
      </Text>
    )
  }
  return (
    <ScrollArea.Autosize mah={280}>
      <Table highlightOnHover stickyHeader>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Span type</Table.Th>
            <Table.Th ta="right">Spans</Table.Th>
            <Table.Th ta="right">Documents</Table.Th>
            <Table.Th ta="right">Forms</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {types.map((type) => {
            const isSelected =
              selected?.text === type.text && selected.label === type.label
            return (
              <Table.Tr
                key={`${type.label}\u0000${type.text}`}
                onClick={() => onSelect(type)}
                bg={
                  isSelected ? 'var(--mantine-primary-color-light)' : undefined
                }
                style={{ cursor: 'pointer' }}
              >
                <Table.Td>
                  <SpanBadge text={type.text} label={type.label} />
                </Table.Td>
                <Table.Td ta="right">{type.spans}</Table.Td>
                <Table.Td ta="right">{type.documents}</Table.Td>
                <Table.Td ta="right">{type.variants}</Table.Td>
              </Table.Tr>
            )
          })}
        </Table.Tbody>
      </Table>
    </ScrollArea.Autosize>
  )
}

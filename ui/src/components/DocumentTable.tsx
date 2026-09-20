import { Table, Text } from '@mantine/core'

import type { Document, Field } from '../api'
import { FieldValueView } from './FieldValueView'

interface Props {
  fields: Field[]
  documents: Document[]
  selectedId: string | null
  onSelect: (document: Document) => void
}

export function DocumentTable({
  fields,
  documents,
  selectedId,
  onSelect,
}: Props) {
  return (
    <Table highlightOnHover stickyHeader>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>ID</Table.Th>
          <Table.Th>Text</Table.Th>
          {fields.map((field) => (
            <Table.Th key={field.name}>{field.name}</Table.Th>
          ))}
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {documents.map((document) => (
          <Table.Tr
            key={document.id}
            onClick={() => onSelect(document)}
            bg={
              document.id === selectedId
                ? 'var(--mantine-primary-color-light)'
                : undefined
            }
            style={{ cursor: 'pointer' }}
          >
            <Table.Td>{document.id}</Table.Td>
            <Table.Td maw={240}>
              <Text truncate>{document.text}</Text>
            </Table.Td>
            {fields.map((field) => (
              <Table.Td key={field.name}>
                <FieldValueView
                  field={field}
                  value={document.values[field.name]}
                />
              </Table.Td>
            ))}
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  )
}

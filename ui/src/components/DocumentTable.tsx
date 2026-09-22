import { Group, Table, Text } from '@mantine/core'
import {
  IconArrowsSort,
  IconSortAscending,
  IconSortDescending,
} from '@tabler/icons-react'
import type { ReactNode } from 'react'

import type { Document, Field, Sort } from '../api'
import { FieldValueView } from './FieldValueView'

interface Props {
  fields: Field[]
  documents: Document[]
  selectedId: string | null
  onSelect: (document: Document) => void
  sort: Sort | null
  onSort: (field: string) => void
}

// point_2d fields have no single orderable value, so they're not sortable.
function isSortable(field: Field): boolean {
  return field.type !== 'point_2d'
}

interface SortableHeaderProps {
  field: string
  sortable?: boolean
  sort: Sort | null
  onSort: (field: string) => void
  children: ReactNode
}

function SortableHeader({
  field,
  sortable = true,
  sort,
  onSort,
  children,
}: SortableHeaderProps) {
  if (!sortable) return <Table.Th>{children}</Table.Th>

  const active = sort?.field === field
  const Icon = active
    ? sort.dir === 'asc'
      ? IconSortAscending
      : IconSortDescending
    : IconArrowsSort

  return (
    <Table.Th
      onClick={() => onSort(field)}
      style={{ cursor: 'pointer', userSelect: 'none' }}
    >
      <Group gap={4} wrap="nowrap">
        {children}
        <Icon size={14} opacity={active ? 1 : 0.4} />
      </Group>
    </Table.Th>
  )
}

export function DocumentTable({
  fields,
  documents,
  selectedId,
  onSelect,
  sort,
  onSort,
}: Props) {
  return (
    <Table highlightOnHover stickyHeader>
      <Table.Thead>
        <Table.Tr>
          <SortableHeader field="id" sort={sort} onSort={onSort}>
            ID
          </SortableHeader>
          <SortableHeader field="text" sort={sort} onSort={onSort}>
            Text
          </SortableHeader>
          {fields.map((field) => (
            <SortableHeader
              key={field.name}
              field={field.name}
              sortable={isSortable(field)}
              sort={sort}
              onSort={onSort}
            >
              {field.name}
            </SortableHeader>
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

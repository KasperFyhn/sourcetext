import { Table, Text } from '@mantine/core'
import { useMemo } from 'react'

import type { CrosstabCell } from '../api'
import { NO_VALUE_LABEL } from '../colors'
import { categoryKeys } from '../plotting'

export interface MatrixCell {
  row: string
  col: string
}

interface Props {
  rowField: string
  colField: string
  cells: CrosstabCell[]
  selected: MatrixCell | null
  // Never called for a "(no value)" row or column, which no filter can express.
  onSelect: (cell: MatrixCell) => void
}

// Cells are shaded by their share of the row (e.g. of all gold "negative"
// documents, how many were predicted "positive"), so each row reads as one
// distribution regardless of class size.
function shade(share: number): string {
  return `color-mix(in srgb, var(--mantine-color-text) ${Math.round(share * 28)}%, transparent)`
}

const cellKey = (row: string, col: string) => `${row}\u0000${col}`

export function ConfusionMatrix({
  rowField,
  colField,
  cells,
  selected,
  onSelect,
}: Props) {
  const { rows, cols, counts, rowTotals, colTotals, total } = useMemo(() => {
    const counts = new Map<string, number>()
    const rowTotals = new Map<string, number>()
    const colTotals = new Map<string, number>()
    let total = 0
    for (const cell of cells) {
      const row = cell.row ?? NO_VALUE_LABEL
      const col = cell.col ?? NO_VALUE_LABEL
      counts.set(cellKey(row, col), cell.count)
      rowTotals.set(row, (rowTotals.get(row) ?? 0) + cell.count)
      colTotals.set(col, (colTotals.get(col) ?? 0) + cell.count)
      total += cell.count
    }
    return {
      rows: categoryKeys(cells.map((cell) => cell.row)),
      cols: categoryKeys(cells.map((cell) => cell.col)),
      counts,
      rowTotals,
      colTotals,
      total,
    }
  }, [cells])

  return (
    <Table
      withTableBorder
      withColumnBorders
      w="auto"
      style={{ alignSelf: 'center' }}
    >
      <Table.Thead>
        <Table.Tr>
          <Table.Th>
            <Text size="xs" c="dimmed">
              {rowField} ↓ · {colField} →
            </Text>
          </Table.Th>
          {cols.map((col) => (
            <Table.Th key={col} ta="center">
              {col}
            </Table.Th>
          ))}
          <Table.Th ta="center">
            <Text size="xs" c="dimmed">
              Total
            </Text>
          </Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.map((row) => {
          const rowTotal = rowTotals.get(row) ?? 0
          return (
            <Table.Tr key={row}>
              <Table.Th>{row}</Table.Th>
              {cols.map((col) => {
                const count = counts.get(cellKey(row, col)) ?? 0
                const share = rowTotal > 0 ? count / rowTotal : 0
                const clickable =
                  count > 0 && row !== NO_VALUE_LABEL && col !== NO_VALUE_LABEL
                const isSelected =
                  selected?.row === row && selected?.col === col
                return (
                  <Table.Td
                    key={col}
                    ta="center"
                    miw={72}
                    style={{
                      backgroundColor: shade(share),
                      cursor: clickable ? 'pointer' : undefined,
                      outline: isSelected
                        ? '2px solid var(--mantine-color-yellow-6)'
                        : undefined,
                      outlineOffset: -2,
                    }}
                    onClick={() => clickable && onSelect({ row, col })}
                  >
                    <Text fw={600} span>
                      {count}
                    </Text>{' '}
                    <Text size="xs" c="dimmed" span>
                      {Math.round(share * 100)}%
                    </Text>
                  </Table.Td>
                )
              })}
              <Table.Td ta="center">{rowTotal}</Table.Td>
            </Table.Tr>
          )
        })}
        <Table.Tr>
          <Table.Th>
            <Text size="xs" c="dimmed">
              Total
            </Text>
          </Table.Th>
          {cols.map((col) => (
            <Table.Td key={col} ta="center">
              {colTotals.get(col) ?? 0}
            </Table.Td>
          ))}
          <Table.Td ta="center">{total}</Table.Td>
        </Table.Tr>
      </Table.Tbody>
    </Table>
  )
}

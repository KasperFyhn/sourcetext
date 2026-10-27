import { YearPickerInput } from '@mantine/dates'

import { setFieldFilter } from '../filters'
import type { ControlProps } from '../filters'

// YearPickerInput's value is an ISO date string (e.g. "2021-01-01"), but the filter
// stores just the year, matching what the backend's `range` op expects for a
// temporal_year field.
function yearToDate(year: string | number | undefined): string | null {
  return year !== undefined ? `${year}-01-01` : null
}

function dateToYear(date: string | null): string | undefined {
  return date ? date.slice(0, 4) : undefined
}

export function TemporalYearFilter({ field, current, onChange }: ControlProps) {
  const value: [string | null, string | null] = [
    yearToDate(current?.min),
    yearToDate(current?.max),
  ]
  return (
    <YearPickerInput
      type="range"
      label={field.name}
      placeholder="Any"
      value={value}
      onChange={([start, end]) => {
        const min = dateToYear(start)
        const max = dateToYear(end)
        onChange((prev) =>
          setFieldFilter(
            prev,
            field.name,
            min || max ? { field: field.name, op: 'range', min, max } : null,
          ),
        )
      }}
      clearable
      w={220}
    />
  )
}

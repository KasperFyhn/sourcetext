import { DateTimePicker } from '@mantine/dates'

import { setFieldFilter } from '../filters'
import type { ControlProps } from '../filters'

export function TemporalDatetimeFilter({
  field,
  current,
  onChange,
}: ControlProps) {
  const value: [string | null, string | null] = [
    (current?.min as string) ?? null,
    (current?.max as string) ?? null,
  ]
  return (
    <DateTimePicker
      type="range"
      label={field.name}
      placeholder="Any"
      value={value}
      onChange={([start, end]) =>
        onChange((prev) =>
          setFieldFilter(
            prev,
            field.name,
            start || end
              ? {
                  field: field.name,
                  op: 'range',
                  min: start ?? undefined,
                  max: end ?? undefined,
                }
              : null,
          ),
        )
      }
      clearable
      w={280}
    />
  )
}

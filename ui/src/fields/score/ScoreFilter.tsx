import { setFieldFilter } from '../filters'
import type { ControlProps } from '../filters'
import { ScoreRange } from './ScoreRange'

export function ScoreFilter({ field, current, onChange }: ControlProps) {
  return (
    <ScoreRange
      label={field.name}
      field={field}
      min={current?.min as number | undefined}
      max={current?.max as number | undefined}
      onChange={(min, max) =>
        onChange((prev) =>
          setFieldFilter(
            prev,
            field.name,
            min !== undefined || max !== undefined
              ? { field: field.name, op: 'range', min, max }
              : null,
          ),
        )
      }
    />
  )
}

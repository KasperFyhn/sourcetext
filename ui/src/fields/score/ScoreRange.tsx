import { Group } from '@mantine/core'

import type { Field } from '../../api/types'
import { stepForRange } from '../../lib/numbers'
import { SteppedNumberInput } from './SteppedNumberInput'

interface ScoreRangeProps {
  label?: string
  placeholders?: [string, string]
  field: Field
  min: number | undefined
  max: number | undefined
  onChange: (min: number | undefined, max: number | undefined) => void
}

// Min and max inputs within a field's numeric bounds (`field.min`/`field.max`).
export function ScoreRange({
  label,
  placeholders = ['min', 'max'],
  field,
  min,
  max,
  onChange,
}: ScoreRangeProps) {
  const bound = (b: number | string | null | undefined): number | undefined =>
    typeof b === 'number' ? b : undefined
  const fieldMin = bound(field.min)
  const fieldMax = bound(field.max)
  const step = stepForRange(fieldMin, fieldMax)
  return (
    <Group gap={4} wrap="nowrap" align="flex-end">
      <SteppedNumberInput
        label={label}
        placeholder={
          fieldMin != null ? `${placeholders[0]} ${fieldMin}` : placeholders[0]
        }
        value={min}
        min={fieldMin}
        max={fieldMax}
        step={step}
        onChange={(v) => onChange(v, max)}
      />
      <SteppedNumberInput
        placeholder={
          fieldMax != null ? `${placeholders[1]} ${fieldMax}` : placeholders[1]
        }
        value={max}
        min={fieldMin}
        max={fieldMax}
        step={step}
        onChange={(v) => onChange(min, v)}
      />
    </Group>
  )
}

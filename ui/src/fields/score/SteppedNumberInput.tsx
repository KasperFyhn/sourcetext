import { ActionIcon, NumberInput, Stack } from '@mantine/core'
import { IconChevronDown, IconChevronUp } from '@tabler/icons-react'

import { clamp } from '../../lib/numbers'

interface SteppedNumberInputProps {
  label?: string
  placeholder: string
  value: number | undefined
  min: number | undefined
  max: number | undefined
  step: number
  onChange: (value: number | undefined) => void
}

// Custom up/down controls rather than NumberInput's built-in ones: from an empty
// value, the down button starts at the field's minimum and the up button starts
// at its maximum, rather than both counting up/down from an arbitrary default.
export function SteppedNumberInput({
  label,
  placeholder,
  value,
  min,
  max,
  step,
  onChange,
}: SteppedNumberInputProps) {
  const increment = () =>
    onChange(value !== undefined ? clamp(value + step, min, max) : (max ?? 0))
  const decrement = () =>
    onChange(value !== undefined ? clamp(value - step, min, max) : (min ?? 0))
  return (
    <NumberInput
      label={label}
      placeholder={placeholder}
      value={value ?? ''}
      min={min}
      max={max}
      step={step}
      clampBehavior="strict"
      hideControls
      withKeyboardEvents={false}
      onChange={(v) => onChange(typeof v === 'number' ? v : undefined)}
      rightSectionWidth={18}
      rightSectionPointerEvents="all"
      rightSection={
        <Stack gap={0}>
          <ActionIcon
            variant="subtle"
            size={16}
            tabIndex={-1}
            aria-label="Increment"
            disabled={max !== undefined && value !== undefined && value >= max}
            onClick={increment}
          >
            <IconChevronUp size={10} />
          </ActionIcon>
          <ActionIcon
            variant="subtle"
            size={16}
            tabIndex={-1}
            aria-label="Decrement"
            disabled={min !== undefined && value !== undefined && value <= min}
            onClick={decrement}
          >
            <IconChevronDown size={10} />
          </ActionIcon>
        </Stack>
      }
      w={120}
    />
  )
}

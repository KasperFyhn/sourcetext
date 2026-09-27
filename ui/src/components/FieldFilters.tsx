import {
  ActionIcon,
  Chip,
  Group,
  NumberInput,
  Stack,
  Text,
  TextInput,
} from '@mantine/core'
import {
  DatePickerInput,
  DateTimePicker,
  YearPickerInput,
} from '@mantine/dates'
import { useDebouncedValue } from '@mantine/hooks'
import { IconChevronDown, IconChevronUp } from '@tabler/icons-react'
import type { Dispatch, SetStateAction } from 'react'
import { useEffect, useState } from 'react'

import type { Field, FieldFilter } from '../api'

interface Props {
  fields: Field[]
  filters: FieldFilter[]
  onChange: Dispatch<SetStateAction<FieldFilter[]>>
}

interface ControlProps {
  field: Field
  current?: FieldFilter
  onChange: Dispatch<SetStateAction<FieldFilter[]>>
}

function setFieldFilter(
  filters: FieldFilter[],
  fieldName: string,
  filter: FieldFilter | null,
): FieldFilter[] {
  const rest = filters.filter((f) => f.field !== fieldName)
  return filter ? [...rest, filter] : rest
}

// Toggle chips rather than a MultiSelect: a MultiSelect's selected-value pills grow
// the input (pushing the rest of the page down as you filter) and its placeholder
// lingers as a visible "Any" tag alongside real selections. Chips have a fixed
// footprint from the start — every option is always shown, just highlighted when
// selected — so nothing shifts as the filter changes.
function LabelOrGroupFilter({ field, current, onChange }: ControlProps) {
  const options = (field.values ?? []).map(String)
  return (
    <Chip.Group
      multiple
      value={current?.values ?? []}
      onChange={(values) =>
        onChange((prev) =>
          setFieldFilter(
            prev,
            field.name,
            values.length > 0 ? { field: field.name, op: 'in', values } : null,
          ),
        )
      }
    >
      <Stack gap={4}>
        <Text size="sm" fw={500}>
          {field.name}
        </Text>
        <Group gap={6}>
          {options.map((option) => (
            <Chip key={option} value={option} size="xs" variant="outline">
              {option}
            </Chip>
          ))}
        </Group>
      </Stack>
    </Chip.Group>
  )
}

function clamp(
  value: number,
  min: number | undefined,
  max: number | undefined,
): number {
  let v = value
  if (min !== undefined) v = Math.max(v, min)
  if (max !== undefined) v = Math.min(v, max)
  return v
}

// A step at the order of magnitude of the field's actual range (e.g. 0.01 for a
// 0-1 score, 1 for a 20-90 range, 100 for a 0-1000 range), rather than a fixed
// step of 1 across every field regardless of scale.
function stepForRange(
  min: number | undefined,
  max: number | undefined,
): number {
  if (min === undefined || max === undefined) return 1
  const range = Math.abs(max - min)
  if (range === 0) return 1
  const exponent = Math.floor(Math.log10(range)) - 1
  return Math.pow(10, exponent)
}

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
function SteppedNumberInput({
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

function ScoreFilter({ field, current, onChange }: ControlProps) {
  const bound = (b: number | string | null | undefined): number | undefined =>
    typeof b === 'number' ? b : undefined
  const fieldMin = bound(field.min)
  const fieldMax = bound(field.max)
  const step = stepForRange(fieldMin, fieldMax)
  const min = current?.min as number | undefined
  const max = current?.max as number | undefined
  const update = (nextMin: number | undefined, nextMax: number | undefined) =>
    onChange((prev) =>
      setFieldFilter(
        prev,
        field.name,
        nextMin !== undefined || nextMax !== undefined
          ? { field: field.name, op: 'range', min: nextMin, max: nextMax }
          : null,
      ),
    )
  return (
    <Group gap={4} wrap="nowrap" align="flex-end">
      <SteppedNumberInput
        label={field.name}
        placeholder={fieldMin != null ? `min ${fieldMin}` : 'min'}
        value={min}
        min={fieldMin}
        max={fieldMax}
        step={step}
        onChange={(v) => update(v, max)}
      />
      <SteppedNumberInput
        placeholder={fieldMax != null ? `max ${fieldMax}` : 'max'}
        value={max}
        min={fieldMin}
        max={fieldMax}
        step={step}
        onChange={(v) => update(min, v)}
      />
    </Group>
  )
}

// YearPickerInput's value is an ISO date string (e.g. "2021-01-01"), but the filter
// stores just the year, matching what the backend's `range` op expects for a
// temporal_year field.
function yearToDate(year: string | number | undefined): string | null {
  return year !== undefined ? `${year}-01-01` : null
}

function dateToYear(date: string | null): string | undefined {
  return date ? date.slice(0, 4) : undefined
}

function TemporalYearFilter({ field, current, onChange }: ControlProps) {
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

function TemporalDateFilter({ field, current, onChange }: ControlProps) {
  const value: [string | null, string | null] = [
    (current?.min as string) ?? null,
    (current?.max as string) ?? null,
  ]
  return (
    <DatePickerInput
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
      w={240}
    />
  )
}

function TemporalDatetimeFilter({ field, current, onChange }: ControlProps) {
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

function TextFilter({ field, current, onChange }: ControlProps) {
  const [text, setText] = useState(current?.text ?? '')
  const [debounced] = useDebouncedValue(text, 300)

  useEffect(() => {
    onChange((prev) =>
      setFieldFilter(
        prev,
        field.name,
        debounced
          ? { field: field.name, op: 'contains', text: debounced }
          : null,
      ),
    )
    // Intentionally depends only on the debounced value (and the field it belongs
    // to) — `onChange` uses React's functional-update form, so it always applies
    // against the latest filters regardless of what else changed in between.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, field.name])

  return (
    <TextInput
      label={field.name}
      placeholder="Contains…"
      value={text}
      onChange={(e) => setText(e.currentTarget.value)}
      w={200}
    />
  )
}

// Shared between TabularView and ScatterView: purely controlled by `filters` +
// `onChange`, so each view can keep its own independent filter state while reusing
// the same per-type controls. point_2d fields have no single filterable value (same
// reasoning as them being unsortable), so they're skipped.
export function FieldFilters({ fields, filters, onChange }: Props) {
  const filterable = fields.filter((f) => f.type !== 'point_2d')
  if (filterable.length === 0) return null

  return (
    <Group align="flex-start" gap="lg">
      {filterable.map((field) => {
        const current = filters.find((f) => f.field === field.name)
        if (field.type === 'label' || field.type === 'group')
          return (
            <LabelOrGroupFilter
              key={field.name}
              field={field}
              current={current}
              onChange={onChange}
            />
          )
        if (field.type === 'score')
          return (
            <ScoreFilter
              key={field.name}
              field={field}
              current={current}
              onChange={onChange}
            />
          )
        if (field.type === 'temporal_year')
          return (
            <TemporalYearFilter
              key={field.name}
              field={field}
              current={current}
              onChange={onChange}
            />
          )
        if (field.type === 'temporal_date')
          return (
            <TemporalDateFilter
              key={field.name}
              field={field}
              current={current}
              onChange={onChange}
            />
          )
        if (field.type === 'temporal_datetime')
          return (
            <TemporalDatetimeFilter
              key={field.name}
              field={field}
              current={current}
              onChange={onChange}
            />
          )
        return (
          <TextFilter
            key={field.name}
            field={field}
            current={current}
            onChange={onChange}
          />
        )
      })}
    </Group>
  )
}

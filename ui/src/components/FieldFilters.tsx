import {
  ActionIcon,
  Chip,
  Group,
  Input,
  NativeSelect,
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

import type { Field, FieldFilter, Filter, SearchFilter } from '../api'
import { LabelDefinitionInfo } from './LabelDefinition'

interface Props {
  fields: Field[]
  filters: Filter[]
  onChange: Dispatch<SetStateAction<Filter[]>>
}

interface ControlProps {
  field: Field
  current?: FieldFilter
  onChange: Dispatch<SetStateAction<Filter[]>>
}

// The filter on the field `fieldName`, if any (never the search filter).
function findFieldFilter(
  filters: Filter[],
  fieldName: string,
): FieldFilter | undefined {
  return filters.find(
    (f): f is FieldFilter => f.op !== 'search' && f.field === fieldName,
  )
}

function setFieldFilter(
  filters: Filter[],
  fieldName: string,
  filter: FieldFilter | null,
): Filter[] {
  const rest = filters.filter((f) => f !== findFieldFilter(filters, fieldName))
  return filter ? [...rest, filter] : rest
}

function LabelFilter({ field, current, onChange }: ControlProps) {
  const options = (field.values ?? []).map(String)
  return (
    <Chip.Group
      multiple
      value={(current?.values ?? []).filter((v) => v !== null)}
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
      <Input.Wrapper label={field.name}>
        <Group gap={6} mih={36}>
          {options.map((option) => (
            <Chip key={option} value={option} size="xs" variant="outline">
              {option}{' '}
              <LabelDefinitionInfo
                definitions={field.definitions}
                value={option}
              />
            </Chip>
          ))}
        </Group>
      </Input.Wrapper>
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

interface ScoreRangeProps {
  label?: string
  placeholders?: [string, string]
  field: Field
  min: number | undefined
  max: number | undefined
  onChange: (min: number | undefined, max: number | undefined) => void
}

// Min and max inputs within a field's numeric bounds (`field.min`/`field.max`).
function ScoreRange({
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

function ScoreFilter({ field, current, onChange }: ControlProps) {
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

// A Chip value standing for unlabelled spans (a label filter's null).
const NO_LABEL_VALUE = '\u0000'
export const NO_LABEL = '(no label)'

interface SpanFilterProps extends ControlProps {
  // Spans per label (null: unlabelled), shown on the label chips if given.
  labelCounts?: Map<string | null, number>
}

// One "span" filter for a span field: label chips, a score range, and a search in
// span text and norm text. It narrows the documents to those with a matching span,
// and prunes the field's spans everywhere to the matching ones.
export function SpanFilter({
  field,
  current,
  onChange,
  labelCounts,
}: SpanFilterProps) {
  const [text, setText] = useState(current?.text ?? '')
  const [debounced] = useDebouncedValue(text, 300)

  const update = (patch: Partial<FieldFilter>) =>
    onChange((prev) => {
      const existing = findFieldFilter(prev, field.name)
      const next: FieldFilter = {
        ...existing,
        ...patch,
        field: field.name,
        op: 'span',
      }
      const empty =
        !next.values?.length &&
        next.min === undefined &&
        next.max === undefined &&
        !next.text
      return setFieldFilter(prev, field.name, empty ? null : next)
    })

  useEffect(() => {
    update({ text: debounced || undefined })
    // Depends only on the debounced value, as in SearchBox: `update` applies
    // against the latest filters through the functional-update form.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, field.name])

  const labels = (field.values ?? []).map((v) =>
    v === null ? null : String(v),
  )
  return (
    <Input.Wrapper label={field.name}>
      <Stack gap={6}>
        <Chip.Group
          multiple
          value={(current?.values ?? []).map((v) => v ?? NO_LABEL_VALUE)}
          onChange={(values) =>
            update({
              values:
                values.length > 0
                  ? values.map((v) => (v === NO_LABEL_VALUE ? null : v))
                  : undefined,
            })
          }
        >
          <Group gap={6}>
            {labels.map((label) => (
              <Chip
                key={label ?? NO_LABEL_VALUE}
                value={label ?? NO_LABEL_VALUE}
                size="xs"
                variant="outline"
              >
                {label ?? NO_LABEL}
                {labelCounts && (
                  <Text span size="xs" opacity={0.6} ml={4}>
                    {labelCounts.get(label) ?? 0}
                  </Text>
                )}
              </Chip>
            ))}
          </Group>
        </Chip.Group>
        <Group gap="xs" align="flex-end">
          {field.min != null && (
            <ScoreRange
              placeholders={['score ≥', 'score ≤']}
              field={field}
              min={current?.min as number | undefined}
              max={current?.max as number | undefined}
              onChange={(min, max) => update({ min, max })}
            />
          )}
          <TextInput
            placeholder="Search spans…"
            value={text}
            onChange={(e) => setText(e.currentTarget.value)}
            w={200}
          />
        </Group>
      </Stack>
    </Input.Wrapper>
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

// The search box's dropdown value for "every text field".
const ALL_TEXT = '\u0000all'

interface SearchBoxProps {
  // The TextType fields the dropdown offers besides the source text.
  textFields: Field[]
  filters: Filter[]
  onChange: Dispatch<SetStateAction<Filter[]>>
}

// One search box for the source text ("text", the default) or the TextType field
// picked in its dropdown, or all of them at once. It's the only search filter.
function SearchBox({ textFields, filters, onChange }: SearchBoxProps) {
  const current = filters.find((f): f is SearchFilter => f.op === 'search')
  const [text, setText] = useState(current?.text ?? '')
  const [target, setTarget] = useState(
    !current
      ? 'text'
      : current.fields.length > 1
        ? ALL_TEXT
        : current.fields[0],
  )
  const [debounced] = useDebouncedValue(text, 300)

  useEffect(() => {
    onChange((prev) => {
      const rest = prev.filter((f) => f.op !== 'search')
      // Same array if nothing changes, so mounting doesn't trigger a refetch.
      if (!debounced) return rest.length === prev.length ? prev : rest
      const fields =
        target === ALL_TEXT
          ? ['text', ...textFields.map((f) => f.name)]
          : [target]
      return [...rest, { op: 'search', text: debounced, fields }]
    })
    // Depends only on the debounced value and the target, as in SpanFilter:
    // `onChange` applies against the latest filters through the functional form.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, target])

  const options = [
    { value: 'text', label: 'text' },
    ...textFields.map((f) => ({ value: f.name, label: f.name })),
    { value: ALL_TEXT, label: 'all text' },
  ]
  const selectedLabel = options.find((o) => o.value === target)?.label ?? 'text'

  const input = (
    <TextInput
      aria-label="Search text"
      placeholder={'Search...'}
      value={text}
      onChange={(e) => setText(e.currentTarget.value)}
      w={170}
      // Joined to the dropdown: square left corners, sharing its border.
      styles={
        textFields.length > 0
          ? {
              input: {
                borderTopLeftRadius: 0,
                borderBottomLeftRadius: 0,
                marginLeft: -1,
              },
            }
          : undefined
      }
    />
  )

  return (
    <Input.Wrapper label="search">
      {textFields.length > 0 ? (
        <Group gap={0} wrap="nowrap">
          <NativeSelect
            aria-label="Search in"
            value={target}
            onChange={(e) => setTarget(e.currentTarget.value)}
            data={options}
            // The full name on hover, since a long one is cut off.
            title={selectedLabel}
            rightSectionWidth={24}
            styles={{
              input: {
                width: 'auto',
                maxWidth: 100,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                paddingRight: 20,
                borderTopRightRadius: 0,
                borderBottomRightRadius: 0,
                backgroundColor: 'var(--mantine-color-default-hover)',
              },
            }}
          />
          {input}
        </Group>
      ) : (
        input
      )}
    </Input.Wrapper>
  )
}

// Shared between TabularView and ScatterView: purely controlled by `filters` +
// `onChange`, so each view can keep its own independent filter state while reusing
// the same per-type controls. point_2d fields have no single filterable value (same
// reasoning as them being unsortable), so they're skipped; text fields are searched
// through the one SearchBox rather than a control each.
export function FieldFilters({ fields, filters, onChange }: Props) {
  const filterable = fields.filter(
    (f) => f.type !== 'point_2d' && f.type !== 'text',
  )

  return (
    <Group align="flex-start" gap="lg">
      <SearchBox
        textFields={fields.filter((f) => f.type === 'text')}
        filters={filters}
        onChange={onChange}
      />
      {filterable.map((field) => {
        const current = findFieldFilter(filters, field.name)
        if (field.type === 'label')
          return (
            <LabelFilter
              key={field.name}
              field={field}
              current={current}
              onChange={onChange}
            />
          )
        if (field.type === 'span')
          return (
            <SpanFilter
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
        return null
      })}
    </Group>
  )
}

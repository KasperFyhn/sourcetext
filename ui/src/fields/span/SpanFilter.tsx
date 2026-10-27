import { Chip, Group, Input, Stack, Text, TextInput } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import { useEffect, useState } from 'react'

import type { FieldFilter } from '../../api/types'
import { findFieldFilter, setFieldFilter } from '../filters'
import type { ControlProps } from '../filters'
import { ScoreRange } from '../score/ScoreRange'

// A Chip value standing for unlabelled spans (a label filter's null).
const NO_LABEL_VALUE = '\u0000'
const NO_LABEL = '(no label)'

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

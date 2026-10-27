import { Group, Input, NativeSelect, TextInput } from '@mantine/core'
import { useDebouncedValue } from '@mantine/hooks'
import type { Dispatch, SetStateAction } from 'react'
import { useEffect, useState } from 'react'

import type { Field, Filter, SearchFilter } from '../../api/types'

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
export function SearchBox({ textFields, filters, onChange }: SearchBoxProps) {
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

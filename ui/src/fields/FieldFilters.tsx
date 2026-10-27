import { Group } from '@mantine/core'
import type { Dispatch, SetStateAction } from 'react'

import type { Field, Filter } from '../api/types'
import { findFieldFilter } from './filters'
import { LabelFilter } from './label/LabelFilter'
import { ScoreFilter } from './score/ScoreFilter'
import { SpanFilter } from './span/SpanFilter'
import { TemporalDateFilter } from './temporal/TemporalDateFilter'
import { TemporalDatetimeFilter } from './temporal/TemporalDatetimeFilter'
import { TemporalYearFilter } from './temporal/TemporalYearFilter'
import { SearchBox } from './text/SearchBox'

interface Props {
  fields: Field[]
  filters: Filter[]
  onChange: Dispatch<SetStateAction<Filter[]>>
}

// Shared by the views: purely controlled by `filters` +
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

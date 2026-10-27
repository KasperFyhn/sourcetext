import type { Dispatch, SetStateAction } from 'react'

import type { Field, FieldFilter, Filter } from '../api/types'

export interface ControlProps {
  field: Field
  current?: FieldFilter
  onChange: Dispatch<SetStateAction<Filter[]>>
}

// The filter on the field `fieldName`, if any (never the search filter).
export function findFieldFilter(
  filters: Filter[],
  fieldName: string,
): FieldFilter | undefined {
  return filters.find(
    (f): f is FieldFilter => f.op !== 'search' && f.field === fieldName,
  )
}

export function setFieldFilter(
  filters: Filter[],
  fieldName: string,
  filter: FieldFilter | null,
): Filter[] {
  const rest = filters.filter((f) => f !== findFieldFilter(filters, fieldName))
  return filter ? [...rest, filter] : rest
}

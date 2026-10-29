export interface Field {
  name: string
  type:
    | 'label'
    | 'score'
    | 'temporal_year'
    | 'temporal_date'
    | 'temporal_datetime'
    | 'text'
    | 'point_2d'
    | 'span'
  // Filter metadata: distinct values for label fields (an "in" filter's
  // candidates), or the min/max bound for score/temporal fields (a "range"
  // filter's domain). Temporal bounds are ISO date/datetime strings. For span
  // fields: their distinct labels (null for unlabelled spans) and score bounds.
  values?: (string | number | null)[] | null
  min?: number | string | null
  max?: number | string | null
  // Label fields only: what each value means (arbitrary JSON per value).
  definitions?: Record<string, unknown> | null
}

export type FilterOp = 'in' | 'range' | 'span'

// A "span" filter matches documents with at least one span in the span field
// `field` with a label among `values` (null: unlabelled), a score within
// `min`/`max`, `text` in its span text or norm text, and exactly `typeText` as its
// type text. It also prunes that field's spans everywhere else: counts, badges and
// highlights only include the spans it matches.
export interface FieldFilter {
  field: string
  op: FilterOp
  values?: (string | null)[]
  min?: number | string
  max?: number | string
  text?: string
  typeText?: string
}

// Documents where any of `fields` contains `text` (ignoring case). A field is a
// text field's name, or 'text' for the source text.
export interface SearchFilter {
  op: 'search'
  text: string
  fields: string[]
}

export type Filter = FieldFilter | SearchFilter

// One span type in a document: the spans sharing a type text (norm text, else
// span text) and label, and how many there are.
export interface SpanTypeCount {
  text: string
  label: string | null
  count: number
}

export type FieldValue =
  string | number | [number, number] | SpanTypeCount[] | null

export interface Document {
  id: string
  text: string
  values: Record<string, FieldValue>
}

export type SortDir = 'asc' | 'desc'

export interface Sort {
  field: string
  dir: SortDir
}

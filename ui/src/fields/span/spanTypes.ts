import type { Span } from '../../api/spans'

// One span type: the spans in a span field sharing a type text and label.
export interface SpanTypeKey {
  field: string
  text: string
  label: string | null
}

export function typeKey({ field, text, label }: SpanTypeKey): string {
  return JSON.stringify([field, label, text])
}

export function spanTypeKey(span: Span): string {
  return typeKey({
    field: span.field,
    text: span.normText ?? span.text,
    label: span.label,
  })
}

interface SpanTypeCount extends SpanTypeKey {
  key: string
  count: number
}

// A document's span types per span field, most frequent first.
export function aggregateSpanTypes(
  spans: Span[],
): Map<string, SpanTypeCount[]> {
  const byKey = new Map<string, SpanTypeCount>()
  for (const span of spans) {
    const key = spanTypeKey(span)
    const existing = byKey.get(key)
    if (existing) existing.count += 1
    else
      byKey.set(key, {
        key,
        field: span.field,
        text: span.normText ?? span.text,
        label: span.label,
        count: 1,
      })
  }
  const byField = new Map<string, SpanTypeCount[]>()
  const sorted = [...byKey.values()].sort(
    (a, b) => b.count - a.count || a.text.localeCompare(b.text),
  )
  for (const type of sorted) {
    byField.set(type.field, [...(byField.get(type.field) ?? []), type])
  }
  return byField
}

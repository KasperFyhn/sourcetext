// A label field's `{value: definition}` map; definitions are arbitrary JSON.
export type LabelDefinitions = Record<string, unknown> | null | undefined

export function definitionOf(
  definitions: LabelDefinitions,
  value: unknown,
): unknown {
  if (value === null || value === undefined) return undefined
  return definitions?.[String(value)]
}

export const formatWeight = (weight: number) =>
  Number.isInteger(weight) ? String(weight) : weight.toFixed(3)

// Keyword-style definitions (e.g. a topic's top words with weights), as
// `[word, weight]` pairs or a `{word: weight}` object; null for anything else.
export function asWeightedTerms(
  definition: unknown,
): [string, number][] | null {
  const entries = Array.isArray(definition)
    ? definition
    : typeof definition === 'object' && definition !== null
      ? Object.entries(definition)
      : null
  if (!entries || entries.length === 0) return null
  const isPair = (entry: unknown) =>
    Array.isArray(entry) &&
    entry.length === 2 &&
    typeof entry[0] === 'string' &&
    typeof entry[1] === 'number'
  return entries.every(isPair) ? (entries as [string, number][]) : null
}

export function isStringList(definition: unknown): definition is string[] {
  return (
    Array.isArray(definition) &&
    definition.every((item) => typeof item === 'string')
  )
}

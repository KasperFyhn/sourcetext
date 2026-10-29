import type { Field, Filter } from './types'

export interface ScatterPoint {
  documentId: string
  x: number
  y: number
  text: string
  group: string | null
}

export interface ScatterData {
  fields: Field[]
  points: ScatterPoint[]
}

export type ScatterQuery = (
  { field: string } | { xField: string; yField: string } | Record<string, never>
) & { colorField?: string; filters?: Filter[] }

export async function fetchScatter(query: ScatterQuery): Promise<ScatterData> {
  const { filters, ...rest } = query
  const entries = Object.entries(rest).filter(
    ([, value]) => value !== undefined,
  )
  const params = new URLSearchParams(
    Object.fromEntries(entries) as Record<string, string>,
  )
  if (filters && filters.length > 0) {
    params.set('filters', JSON.stringify(filters))
  }
  const res = await fetch(`/api/documents/scatter?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<ScatterData>
}

export interface StripPoint {
  documentId: string
  x: number
  text: string
  row: string | null
  color: string | null
}

export interface StripData {
  points: StripPoint[]
}

export interface StripQuery {
  xField: string
  rowField: string
  colorField?: string
  filters?: Filter[]
}

// A strip plot's points: one per document along a score field (`x`), split by a
// label field (`row`), optionally colored by another (`color`).
export async function fetchStrip(query: StripQuery): Promise<StripData> {
  const { filters, ...rest } = query
  const entries = Object.entries(rest).filter(
    ([, value]) => value !== undefined,
  )
  const params = new URLSearchParams(
    Object.fromEntries(entries) as Record<string, string>,
  )
  if (filters && filters.length > 0) {
    params.set('filters', JSON.stringify(filters))
  }
  const res = await fetch(`/api/documents/strip?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json() as Promise<StripData>
}

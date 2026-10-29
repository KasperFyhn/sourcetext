export interface CrosstabCell {
  row: string | null
  col: string | null
  count: number
}

// Document counts per value pair of two label fields (a confusion matrix).
export async function fetchCrosstab(
  rowField: string,
  colField: string,
): Promise<CrosstabCell[]> {
  const params = new URLSearchParams({ rowField, colField })
  const res = await fetch(`/api/documents/crosstab?${params}`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const body = (await res.json()) as { cells: CrosstabCell[] }
  return body.cells
}

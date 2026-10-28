import type { Field } from '../../api/types'
import { GOLD_LABEL, PREDICTION } from '../../lib/namedFields'

// If both named fields are present, the matrix opens as gold labels (rows) vs.
// predictions (columns); otherwise as the first two label fields.
export function defaultMatrixFields(fields: Field[]): {
  row: string | null
  col: string | null
} {
  const names = fields.filter((f) => f.type === 'label').map((f) => f.name)
  if (names.includes(GOLD_LABEL) && names.includes(PREDICTION))
    return { row: GOLD_LABEL, col: PREDICTION }
  if (names.length >= 2) return { row: names[0], col: names[1] }
  return { row: null, col: null }
}

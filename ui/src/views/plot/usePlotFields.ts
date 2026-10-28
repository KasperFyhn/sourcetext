import { fetchScatter } from '../../api/plot'
import { useFetch } from '../../hooks/useFetch'

// Only the fields the plot can use (point_2d, score, label), for the selectors:
// the scatter route lists them when asked for no field.
export function usePlotFields() {
  const { data, error } = useFetch(
    () => fetchScatter({}).then((r) => r.fields),
    [],
  )
  return { plotFields: data, error }
}

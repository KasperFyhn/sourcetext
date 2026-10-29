import { useEffect, useState } from 'react'
import type { DependencyList } from 'react'

interface FetchState<T> {
  data: T | null
  error: string | null
  // The deps the data was loaded for.
  deps: DependencyList | null
}

function sameDeps(a: DependencyList, b: DependencyList): boolean {
  return a.length === b.length && a.every((dep, i) => Object.is(dep, b[i]))
}

// Runs `load` whenever `deps` change and returns its latest result. Results of
// superseded calls are dropped, so a slow earlier request never overwrites a later
// one. Pass `load = null` when there is nothing to fetch: `data` is then null.
// With `keepPrevious` (the default), the previous data stays while new deps load,
// e.g. the current page until the next one arrives; without it, `data` is null
// until data for the current deps is in. An error is kept until a call succeeds.
export function useFetch<T>(
  load: (() => Promise<T>) | null,
  deps: DependencyList,
  { keepPrevious = true }: { keepPrevious?: boolean } = {},
): { data: T | null; error: string | null } {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    error: null,
    deps: null,
  })

  useEffect(() => {
    if (!load) return
    let stale = false
    load()
      .then((data) => !stale && setState({ data, error: null, deps }))
      .catch(
        (err: Error) =>
          !stale && setState((prev) => ({ ...prev, error: err.message })),
      )
    return () => {
      stale = true
    }
    // `deps` stands in for everything `load` uses, as with useEffect itself.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  if (!load) return { data: null, error: state.error }
  const current = state.deps !== null && sameDeps(state.deps, deps)
  return {
    data: keepPrevious || current ? state.data : null,
    error: state.error,
  }
}

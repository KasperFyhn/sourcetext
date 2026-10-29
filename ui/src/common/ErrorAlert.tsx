import { Alert } from '@mantine/core'
import type { MantineSpacing } from '@mantine/core'

// A failed request's message; renders nothing without an error.
export function ErrorAlert({
  error,
  m,
}: {
  error: string | null | undefined
  m?: MantineSpacing
}) {
  if (!error) return null
  return (
    <Alert color="red" title="Something went wrong" m={m}>
      {error}
    </Alert>
  )
}

import { Box, Text } from '@mantine/core'

import type { Document, Field, Filter } from '../api/types'
import type { SpanTypeKey } from '../fields/span/spanTypes'
import { DocumentDetail } from './DocumentDetail'

interface Props {
  fields: Field[]
  document: Document | null
  // The view's filters: "span" filters among them prune the spans listed and
  // highlighted to the ones they match.
  filters?: Filter[]
  // A span type to highlight from the start, e.g. the one a view navigated by.
  highlightType?: SpanTypeKey | null
}

export function DocumentView({
  fields,
  document,
  filters = [],
  highlightType = null,
}: Props) {
  return (
    <Box
      flex={2}
      p="md"
      style={{
        overflowY: 'auto',
        borderLeft: '1px solid var(--mantine-color-default-border)',
      }}
    >
      {!document ? (
        <Text c="dimmed">
          Select a document in the navigation pane to view it.
        </Text>
      ) : (
        <DocumentDetail
          key={document.id}
          fields={fields}
          document={document}
          filters={filters}
          highlightType={highlightType}
        />
      )}
    </Box>
  )
}

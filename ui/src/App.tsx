import { ActionIcon, Box, Flex, Stack, Tooltip } from '@mantine/core'
import {
  IconChartScatter,
  IconGrid3x3,
  IconTextColor,
  IconTable,
} from '@tabler/icons-react'
import { useState } from 'react'

import { NotesFileProvider } from './contexts/NotesFileContext'
import { MatrixView } from './views/matrix/MatrixView'
import { PlotView } from './views/plot/PlotView'
import { SpanView } from './views/spans/SpanView'
import { TabularView } from './views/tabular/TabularView'

type View = 'tabular' | 'plot' | 'matrix' | 'spans'

function App() {
  const [view, setView] = useState<View>('tabular')

  return (
    <NotesFileProvider>
      <Flex h="100vh">
        <Stack
          gap="xs"
          p="xs"
          w={56}
          style={{
            borderRight: '1px solid var(--mantine-color-default-border)',
          }}
        >
          <Tooltip label="Tabular view" position="right">
            <ActionIcon
              variant={view === 'tabular' ? 'filled' : 'subtle'}
              aria-label="Tabular view"
              onClick={() => setView('tabular')}
            >
              <IconTable size={20} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Plot view" position="right">
            <ActionIcon
              variant={view === 'plot' ? 'filled' : 'subtle'}
              aria-label="Plot view"
              onClick={() => setView('plot')}
            >
              <IconChartScatter size={20} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Confusion matrix view" position="right">
            <ActionIcon
              variant={view === 'matrix' ? 'filled' : 'subtle'}
              aria-label="Confusion matrix view"
              onClick={() => setView('matrix')}
            >
              <IconGrid3x3 size={20} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Span view" position="right">
            <ActionIcon
              variant={view === 'spans' ? 'filled' : 'subtle'}
              aria-label="Span view"
              onClick={() => setView('spans')}
            >
              <IconTextColor size={20} />
            </ActionIcon>
          </Tooltip>
        </Stack>
        <Box flex={1} style={{ overflow: 'hidden' }}>
          {view === 'tabular' && <TabularView />}
          {view === 'plot' && <PlotView />}
          {view === 'matrix' && <MatrixView />}
          {view === 'spans' && <SpanView />}
        </Box>
      </Flex>
    </NotesFileProvider>
  )
}

export default App

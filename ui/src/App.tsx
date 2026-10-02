import { ActionIcon, Box, Flex, Stack, Tooltip } from '@mantine/core'
import { IconChartScatter, IconGrid3x3, IconTable } from '@tabler/icons-react'
import { useState } from 'react'

import { MatrixView } from './components/MatrixView'
import { PlotView } from './components/PlotView'
import { TabularView } from './components/TabularView'

type View = 'tabular' | 'plot' | 'matrix'

function App() {
  const [view, setView] = useState<View>('tabular')

  return (
    <Flex h="100vh">
      <Stack
        gap="xs"
        p="xs"
        w={56}
        style={{ borderRight: '1px solid var(--mantine-color-default-border)' }}
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
      </Stack>
      <Box flex={1} style={{ overflow: 'hidden' }}>
        {view === 'tabular' && <TabularView />}
        {view === 'plot' && <PlotView />}
        {view === 'matrix' && <MatrixView />}
      </Box>
    </Flex>
  )
}

export default App

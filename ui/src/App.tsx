import { ActionIcon, Box, Flex, Stack, Tooltip } from '@mantine/core'
import { IconChartScatter, IconTable } from '@tabler/icons-react'
import { useState } from 'react'

import { ScatterView } from './components/ScatterView'
import { TabularView } from './components/TabularView'

type View = 'tabular' | 'scatter'

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
        <Tooltip label="Scatter view" position="right">
          <ActionIcon
            variant={view === 'scatter' ? 'filled' : 'subtle'}
            aria-label="Scatter view"
            onClick={() => setView('scatter')}
          >
            <IconChartScatter size={20} />
          </ActionIcon>
        </Tooltip>
      </Stack>
      <Box flex={1} style={{ overflow: 'hidden' }}>
        {view === 'tabular' ? <TabularView /> : <ScatterView />}
      </Box>
    </Flex>
  )
}

export default App

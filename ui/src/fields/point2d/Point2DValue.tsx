import { Text } from '@mantine/core'

export function Point2DValue({ point }: { point: [number, number] }) {
  const [x, y] = point
  return (
    <Text>
      ({x.toFixed(2)}, {y.toFixed(2)})
    </Text>
  )
}

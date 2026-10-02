import { Divider, Flex, Paper, ScrollArea, Stack, Text } from '@mantine/core'
import { AxisBottom, AxisLeft } from '@visx/axis'
import { Group } from '@visx/group'
import { ParentSize } from '@visx/responsive'
import { scaleLinear } from '@visx/scale'
import { useMemo, useRef, useState } from 'react'

import type { ScatterPoint } from '../api'
import { buildColorScale } from '../colors'

interface Props {
  points: ScatterPoint[]
  xLabel: string
  yLabel: string
  selectedId: string | null
  onSelect: (documentId: string) => void
}

const MARGIN = { top: 16, right: 16, bottom: 40, left: 56 }
const BUCKET_SIZE = 8
const CLOSE_DELAY_MS = 150
const TOOLTIP_WIDTH = 240

// A cluster can straddle a group boundary; color it by whichever group is most
// represented among its points.
function majorityGroup(points: ScatterPoint[]): string | null {
  const counts = new Map<string | null, number>()
  for (const point of points)
    counts.set(point.group, (counts.get(point.group) ?? 0) + 1)
  let best = points[0].group
  let bestCount = 0
  for (const [group, count] of counts) {
    if (count > bestCount) {
      best = group
      bestCount = count
    }
  }
  return best
}

interface Bucket {
  key: string
  px: number
  py: number
  points: ScatterPoint[]
}

function computeDomain(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1]
  const min = Math.min(...values)
  const max = Math.max(...values)
  if (min === max) return [min - 1, max + 1]
  const pad = (max - min) * 0.05
  return [min - pad, max + pad]
}

// Groups points by rendered pixel position rather than exact (x, y) equality: this
// catches both near-identical embedding floats and exact score ties uniformly, and
// keeps clustering purely a rendering concern (the backend returns one row per doc).
function buildBuckets(
  points: ScatterPoint[],
  xScale: (x: number) => number,
  yScale: (y: number) => number,
): Bucket[] {
  const groups = new Map<
    string,
    { sumPx: number; sumPy: number; points: ScatterPoint[] }
  >()
  for (const point of points) {
    const px = xScale(point.x)
    const py = yScale(point.y)
    const key = `${Math.round(px / BUCKET_SIZE)}:${Math.round(py / BUCKET_SIZE)}`
    const group = groups.get(key)
    if (group) {
      group.sumPx += px
      group.sumPy += py
      group.points.push(point)
    } else {
      groups.set(key, { sumPx: px, sumPy: py, points: [point] })
    }
  }
  return Array.from(groups.entries()).map(([key, group]) => ({
    key,
    px: group.sumPx / group.points.length,
    py: group.sumPy / group.points.length,
    points: group.points,
  }))
}

export function ScatterPlot({
  points,
  xLabel,
  yLabel,
  selectedId,
  onSelect,
}: Props) {
  return (
    <div style={{ flexGrow: 1, minHeight: 400, position: 'relative' }}>
      <ParentSize>
        {({ width, height }) =>
          width > 0 && height > 0 ? (
            <ScatterPlotInner
              width={width}
              height={height}
              points={points}
              xLabel={xLabel}
              yLabel={yLabel}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ) : null
        }
      </ParentSize>
    </div>
  )
}

interface InnerProps extends Props {
  width: number
  height: number
}

function ScatterPlotInner({
  width,
  height,
  points,
  xLabel,
  yLabel,
  selectedId,
  onSelect,
}: InnerProps) {
  const [hoveredKey, setHoveredKey] = useState<string | null>(null)
  const closeTimeout = useRef<number | null>(null)

  const cancelClose = () => {
    if (closeTimeout.current !== null) {
      window.clearTimeout(closeTimeout.current)
      closeTimeout.current = null
    }
  }
  const scheduleClose = () => {
    cancelClose()
    closeTimeout.current = window.setTimeout(
      () => setHoveredKey(null),
      CLOSE_DELAY_MS,
    )
  }

  const xScale = useMemo(
    () =>
      scaleLinear<number>({
        domain: computeDomain(points.map((p) => p.x)),
        range: [MARGIN.left, width - MARGIN.right],
      }),
    [points, width],
  )
  const yScale = useMemo(
    () =>
      scaleLinear<number>({
        domain: computeDomain(points.map((p) => p.y)),
        range: [height - MARGIN.bottom, MARGIN.top],
      }),
    [points, height],
  )
  const buckets = useMemo(
    () => buildBuckets(points, xScale, yScale),
    [points, xScale, yScale],
  )
  const hovered = buckets.find((bucket) => bucket.key === hoveredKey) ?? null

  // Only points fetched with a `colorField` carry a non-null group, so this is
  // also how we tell "coloring is active" from "no color field selected" —
  // when it's off, the plot renders exactly as it did before this feature.
  const hasGroups = points.some((point) => point.group != null)
  const colorScale = useMemo(
    () => buildColorScale(points.map((point) => point.group)),
    [points],
  )

  return (
    <div style={{ position: 'relative', width, height }}>
      <svg width={width} height={height}>
        <Group>
          <AxisBottom
            scale={xScale}
            top={height - MARGIN.bottom}
            label={xLabel}
            numTicks={5}
          />
          <AxisLeft
            scale={yScale}
            left={MARGIN.left}
            label={yLabel}
            numTicks={5}
          />
          {buckets.map((bucket) => {
            const count = bucket.points.length
            const radius =
              count === 1 ? 4 : Math.min(4 + Math.log2(count) * 2, 12)
            const isSelected =
              selectedId != null &&
              bucket.points.some((point) => point.documentId === selectedId)
            return (
              <g
                key={bucket.key}
                onMouseEnter={() => {
                  cancelClose()
                  setHoveredKey(bucket.key)
                }}
                onMouseLeave={scheduleClose}
                onClick={() => {
                  // A single-document bucket can be selected directly; a multi-doc
                  // bucket requires picking a specific entry from the hover tooltip.
                  if (count === 1) onSelect(bucket.points[0].documentId)
                }}
                style={{ cursor: 'pointer' }}
              >
                <circle
                  cx={bucket.px}
                  cy={bucket.py}
                  r={radius}
                  fill={
                    hasGroups
                      ? colorScale.colorOf(majorityGroup(bucket.points))
                      : 'var(--mantine-primary-color-filled)'
                  }
                  fillOpacity={0.75}
                  stroke={
                    isSelected
                      ? 'var(--mantine-color-yellow-6)'
                      : 'var(--mantine-color-body)'
                  }
                  strokeWidth={isSelected ? 3 : 1}
                />
                {count > 1 && (
                  <text
                    x={bucket.px}
                    y={bucket.py}
                    dy="0.35em"
                    textAnchor="middle"
                    fontSize={9}
                    fill="var(--mantine-color-white)"
                    style={{ pointerEvents: 'none' }}
                  >
                    {count}
                  </text>
                )}
              </g>
            )
          })}
        </Group>
      </svg>
      {hasGroups && colorScale.legend.length > 1 && (
        <Paper
          shadow="xs"
          withBorder
          p={6}
          style={{ position: 'absolute', top: 8, right: 8 }}
        >
          <Stack gap={4}>
            {colorScale.legend.map((entry) => (
              <Flex key={entry.label} align="center" gap={6}>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: entry.color,
                    flexShrink: 0,
                  }}
                />
                <Text size="xs">{entry.label}</Text>
              </Flex>
            ))}
          </Stack>
        </Paper>
      )}
      {hovered && (
        <ScatterTooltip
          bucket={hovered}
          containerWidth={width}
          containerHeight={height}
          selectedId={selectedId}
          onSelect={onSelect}
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
        />
      )}
    </div>
  )
}

interface TooltipProps {
  bucket: Bucket
  containerWidth: number
  containerHeight: number
  selectedId: string | null
  onSelect: (documentId: string) => void
  onMouseEnter: () => void
  onMouseLeave: () => void
}

function ScatterTooltip({
  bucket,
  containerWidth,
  containerHeight,
  selectedId,
  onSelect,
  onMouseEnter,
  onMouseLeave,
}: TooltipProps) {
  const left = Math.min(bucket.px + 10, containerWidth - TOOLTIP_WIDTH - 4)
  const top = Math.min(Math.max(bucket.py - 10, 4), containerHeight - 48)

  return (
    <Paper
      shadow="md"
      withBorder
      p="xs"
      style={{
        position: 'absolute',
        left,
        top,
        width: TOOLTIP_WIDTH,
        zIndex: 10,
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <ScrollArea h={Math.min(40 * bucket.points.length, 220)} type="auto">
        <Stack gap={4}>
          {bucket.points.map((point, index) => (
            <div
              key={point.documentId}
              onClick={() => onSelect(point.documentId)}
              style={{
                cursor: 'pointer',
                backgroundColor:
                  point.documentId === selectedId
                    ? 'var(--mantine-primary-color-light)'
                    : undefined,
              }}
            >
              {index > 0 && <Divider mb={4} />}
              <Text fw={700} size="xs">
                {point.documentId}
              </Text>
              <Text size="sm" lineClamp={2}>
                {point.text}
              </Text>
            </div>
          ))}
        </Stack>
      </ScrollArea>
    </Paper>
  )
}

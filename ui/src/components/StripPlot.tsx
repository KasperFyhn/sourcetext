import { Flex, Paper, Stack, Text } from '@mantine/core'
import { AxisBottom, AxisLeft } from '@visx/axis'
import { ParentSize } from '@visx/responsive'
import { scaleLinear } from '@visx/scale'
import { useMemo, useState } from 'react'

import type { StripPoint } from '../api'
import { buildColorScale, NO_VALUE_LABEL } from '../colors'
import { categoryKeys, computeDomain } from '../plotting'

// Which axis holds the categories: 'horizontal' lays each category out as a row
// (score on the x axis), 'vertical' as a column (score on the y axis).
export type StripOrientation = 'horizontal' | 'vertical'

interface Props {
  // `x` is the score; `row` is the category, whichever axis it's drawn on.
  points: StripPoint[]
  orientation: StripOrientation
  scoreLabel: string
  categoryLabel: string
  selectedId: string | null
  onSelect: (documentId: string) => void
}

const RADIUS = 4
const BAND_GAP = 8
const MIN_BAND = 48
const TOOLTIP_WIDTH = 260

interface PlacedPoint {
  point: StripPoint
  // Position along the score axis, in pixels.
  pos: number
  // Offset across the score axis from the band's center line, in pixels.
  offset: number
}

// Beeswarm layout: place points in score order, each at the offset closest to the
// center line that doesn't overlap an already-placed neighbor, so every document
// stays an individually visible, clickable dot instead of stacking up. If the swarm
// is wider than its band, offsets are compressed to fit, accepting some overlap
// rather than unbounded band sizes.
function beeswarm(
  points: StripPoint[],
  scale: (value: number) => number,
  halfBand: number,
): PlacedPoint[] {
  const diameter = RADIUS * 2
  const sorted = points
    .map((point) => ({ point, pos: scale(point.x), offset: 0 }))
    .sort((a, b) => a.pos - b.pos)
  const placed: PlacedPoint[] = []
  for (const current of sorted) {
    const neighbors: PlacedPoint[] = []
    for (let i = placed.length - 1; i >= 0; i--) {
      if (current.pos - placed[i].pos >= diameter) break
      neighbors.push(placed[i])
    }
    const candidates = [0]
    for (const neighbor of neighbors) {
      const d = current.pos - neighbor.pos
      const across = Math.sqrt(diameter * diameter - d * d)
      candidates.push(neighbor.offset + across, neighbor.offset - across)
    }
    candidates.sort((a, b) => Math.abs(a) - Math.abs(b))
    const fits = (offset: number) =>
      neighbors.every(
        (n) =>
          (current.pos - n.pos) ** 2 + (offset - n.offset) ** 2 >=
          diameter * diameter - 0.01,
      )
    current.offset = candidates.find(fits) ?? 0
    // Keep `placed` sorted by pos so the neighbor scan above can stop early.
    placed.push(current)
  }
  const maxOffset = Math.max(0, ...placed.map((p) => Math.abs(p.offset)))
  const room = Math.max(halfBand - RADIUS, 0)
  if (maxOffset > room) {
    const factor = room / maxOffset
    for (const p of placed) p.offset *= factor
  }
  return placed
}

export function StripPlot(props: Props) {
  return (
    <div style={{ flexGrow: 1, minHeight: 400, position: 'relative' }}>
      <ParentSize>
        {({ width, height }) =>
          width > 0 && height > 0 ? (
            <StripPlotInner width={width} height={height} {...props} />
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

function StripPlotInner({
  width,
  height,
  points,
  orientation,
  scoreLabel,
  categoryLabel,
  selectedId,
  onSelect,
}: InnerProps) {
  const [hovered, setHovered] = useState<PlacedPoint | null>(null)
  const horizontal = orientation === 'horizontal'

  const keys = useMemo(
    () => categoryKeys(points.map((point) => point.row)),
    [points],
  )
  // Horizontal: category labels on the left, score axis along the bottom.
  // Vertical: score axis on the left, category labels along the bottom.
  const margin = horizontal
    ? {
        top: 8,
        right: 16,
        bottom: 40,
        left: Math.min(24 + Math.max(...keys.map((k) => k.length)) * 7, 180),
      }
    : { top: 16, right: 16, bottom: 48, left: 56 }
  const crossLength = horizontal
    ? height - margin.top - margin.bottom
    : width - margin.left - margin.right
  const band = Math.max(crossLength / Math.max(keys.length, 1), MIN_BAND)
  // Too many categories to fit: the plot grows past its container and scrolls.
  const svgWidth = horizontal
    ? width
    : margin.left + band * keys.length + margin.right
  const svgHeight = horizontal
    ? margin.top + band * keys.length + margin.bottom
    : height

  const scoreScale = useMemo(
    () =>
      scaleLinear<number>({
        domain: computeDomain(points.map((p) => p.x)),
        range: horizontal
          ? [margin.left, width - margin.right]
          : [height - margin.bottom, margin.top],
      }),
    [
      points,
      horizontal,
      margin.left,
      margin.right,
      margin.top,
      margin.bottom,
      width,
      height,
    ],
  )
  const bands = useMemo(
    () =>
      keys.map((key) => ({
        key,
        placed: beeswarm(
          points.filter((p) => (p.row ?? NO_VALUE_LABEL) === key),
          scoreScale,
          (band - BAND_GAP) / 2,
        ),
      })),
    [keys, points, scoreScale, band],
  )

  const hasColors = points.some((point) => point.color != null)
  const colorScale = useMemo(
    () => buildColorScale(points.map((point) => point.color)),
    [points],
  )

  const bandStart = (index: number) =>
    (horizontal ? margin.top : margin.left) + index * band
  const position = (center: number, placed: PlacedPoint) =>
    horizontal
      ? { x: placed.pos, y: center + placed.offset }
      : { x: center + placed.offset, y: placed.pos }
  const hoveredCenter = hovered
    ? bandStart(keys.indexOf(hovered.point.row ?? NO_VALUE_LABEL)) + band / 2
    : 0
  const hoveredAt = hovered ? position(hoveredCenter, hovered) : null

  return (
    <div style={{ position: 'relative', width, height, overflow: 'auto' }}>
      <svg width={svgWidth} height={svgHeight}>
        {bands.map((b, index) => {
          const start = bandStart(index)
          const center = start + band / 2
          return (
            <g key={b.key}>
              <rect
                x={horizontal ? margin.left : start + BAND_GAP / 2}
                y={horizontal ? start + BAND_GAP / 2 : margin.top}
                width={
                  horizontal
                    ? width - margin.left - margin.right
                    : band - BAND_GAP
                }
                height={
                  horizontal
                    ? band - BAND_GAP
                    : height - margin.top - margin.bottom
                }
                fill="var(--mantine-color-default-hover)"
                rx={4}
              />
              <text
                x={horizontal ? margin.left - 8 : center}
                y={horizontal ? center : height - margin.bottom + 16}
                dy={horizontal ? '0.35em' : 0}
                textAnchor={horizontal ? 'end' : 'middle'}
                fontSize={12}
                fill="var(--mantine-color-text)"
              >
                {b.key}
              </text>
              {b.placed.map((placed) => {
                const isSelected = placed.point.documentId === selectedId
                const { x, y } = position(center, placed)
                return (
                  <circle
                    key={placed.point.documentId}
                    cx={x}
                    cy={y}
                    r={RADIUS}
                    fill={
                      hasColors
                        ? colorScale.colorOf(placed.point.color)
                        : 'var(--mantine-primary-color-filled)'
                    }
                    fillOpacity={0.8}
                    stroke={
                      isSelected
                        ? 'var(--mantine-color-yellow-6)'
                        : 'var(--mantine-color-body)'
                    }
                    strokeWidth={isSelected ? 3 : 0.75}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered(placed)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => onSelect(placed.point.documentId)}
                  />
                )
              })}
            </g>
          )
        })}
        {horizontal ? (
          <AxisBottom
            scale={scoreScale}
            top={svgHeight - margin.bottom}
            label={scoreLabel}
            numTicks={6}
          />
        ) : (
          <>
            <AxisLeft
              scale={scoreScale}
              left={margin.left}
              label={scoreLabel}
              numTicks={6}
            />
            <text
              x={(margin.left + svgWidth - margin.right) / 2}
              y={height - 8}
              textAnchor="middle"
              fontSize={10}
              fill="var(--mantine-color-text)"
            >
              {categoryLabel}
            </text>
          </>
        )}
      </svg>
      {hasColors && colorScale.legend.length > 1 && (
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
      {hovered && hoveredAt && (
        <Paper
          shadow="md"
          withBorder
          p="xs"
          style={{
            position: 'absolute',
            left: Math.min(hoveredAt.x + 10, width - TOOLTIP_WIDTH - 4),
            top: Math.max(hoveredAt.y - 10, 4),
            width: TOOLTIP_WIDTH,
            zIndex: 10,
            pointerEvents: 'none',
          }}
        >
          <Text fw={700} size="xs">
            {hovered.point.documentId} · {scoreLabel} {hovered.point.x}
          </Text>
          <Text size="sm" lineClamp={3}>
            {hovered.point.text}
          </Text>
        </Paper>
      )}
    </div>
  )
}

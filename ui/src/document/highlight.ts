export interface TextSegment {
  text: string
  // Code point offset of the segment in the text.
  start: number
  marked: boolean
}

// The text cut into marked and unmarked segments, marking `highlights`. Offsets
// count code points (as Python does), not JS's UTF-16 units, hence `Array.from`.
// Overlapping ranges are merged.
export function highlightSegments(
  text: string,
  highlights: { start: number; end: number }[],
): TextSegment[] {
  if (highlights.length === 0) return [{ text, start: 0, marked: false }]
  const chars = Array.from(text)
  const ranges = [...highlights].sort((a, b) => a.start - b.start)
  const segments: TextSegment[] = []
  let pos = 0
  for (const { start, end } of ranges) {
    if (end <= pos) continue
    const from = Math.max(start, pos)
    segments.push({
      text: chars.slice(pos, from).join(''),
      start: pos,
      marked: false,
    })
    segments.push({
      text: chars.slice(from, end).join(''),
      start: from,
      marked: true,
    })
    pos = end
  }
  segments.push({ text: chars.slice(pos).join(''), start: pos, marked: false })
  return segments
}

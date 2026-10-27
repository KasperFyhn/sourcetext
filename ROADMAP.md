# Roadmap

What's planned for sourcetext, roughly in order. Nothing here is a promise: the
order may change as people use the tool and report what they need. Suggestions are
welcome at
[github.com/KasperFyhn/sourcetext/issues](https://github.com/KasperFyhn/sourcetext/issues).

## Next: finish what's already half-built

These features are accepted by the Python API today but don't do everything they
should yet.

- **Temporal fields on the plot.** `TemporalType` fields can only be filtered by
  today. Allow them as a plot axis, e.g. a score over time or a strip plot of
  documents per year.

## Then: reading and judging

These features help with the main job: reading documents closely and recording
judgments about them.

- **Filter by notes.** Show only documents that have a note, or that have none,
  and search inside notes.
- **Structured judgments.** Alongside free-text notes, let the user mark a
  document with a tag or a corrected label (e.g. "model is wrong, should be
  `positive`"). Judgments go back to Python the same way as notes, so they can be
  reused as new gold labels.
- **Span counts as fields.** Count spans per label or type (e.g. for the confusion
  matrix or as a plot axis).
- **Keyboard navigation.** Step to the previous or next document in the current
  view's order without using the mouse, for reading long lists.

## Later: more ways to look at the data

- **Metrics on the confusion matrix.** Per-class precision, recall and F1, plus
  totals, next to the matrix.
- **Tags.** A field holding several labels/tags per document (e.g.
  multi-label classification or a set of topics).
- **Adding fields after construction.** Attach a new field to an existing
  `SourceText` (e.g. `st.add_field("toxicity", ScoreType(...))`) without
  rebuilding it, so that model output can be compared as it is iterated on.
- **Larger corpora.** At 100k documents with 1M spans, building a `SourceText`
  takes about 15 s and the table, span view and document pane respond in under
  0.4 s. The plot routes still return every document at once: check how they
  scale, and sample or aggregate where needed.

## Internal

Changes to the code that users won't see directly.

- **One filter type per op.** Split `FieldFilter` into `InFilter`, `RangeFilter`
  and `SpanFilter` (next to `SearchFilter`), each with only its own fields, as a
  union on `op` in Python, the request models and TypeScript. Checks like "an `in`
  filter needs `values`" then move from `_apply_filters` into the request models.
  The UI's `SpanFilter` component needs a new name.

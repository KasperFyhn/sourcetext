# Roadmap

What's planned for sourcetext, roughly in order. Nothing here is a promise: the
order may change as people use the tool and report what they need. Suggestions are
welcome at
[github.com/KasperFyhn/sourcetext/issues](https://github.com/KasperFyhn/sourcetext/issues).

## Next: finish what's already half-built

These features are accepted by the Python API today but don't do everything they
should yet.

- **Get notes back into Python.** Today notes can be read back from their JSONL
  file (`pd.read_json(path, lines=True)`), but not from the `SourceText`. Add a way
  to return them to your analysis, e.g. `st.notes` as a DataFrame of
  `(document_id, note)`, or `st.to_dataframe()` with notes as a column.
- **Render spans.** `SpanType` fields (e.g. NER output) are stored but not shown.
  Highlight them in the document pane, coloured by label, with their scores on
  hover.
- **Show group definitions.** Definitions passed via `group_definitions=` /
  `GroupType(definitions=...)` are stored but not shown. Show them next to group
  badges, filter options and plot legends.
- **Temporal fields on the plot.** `TemporalType` fields can only be filtered by
  today. Allow them as a plot axis, e.g. a score over time or a strip plot of
  documents per year.

## Then: reading and judging

These features help with the main job: reading documents closely and recording
judgments about them.

- **Full-text search.** Filter documents by a substring of the source text itself.
  Today the "contains" filter only works on `TextType` fields.
- **Filter by notes.** Show only documents that have a note, or that have none,
  and search inside notes.
- **Structured judgments.** Alongside free-text notes, let the user mark a
  document with a tag or a corrected label (e.g. "model is wrong, should be
  `positive`"). Judgments go back to Python the same way as notes, so they can be
  reused as new gold labels.
- **Spans as filters and fields.** Filter documents by the labels of the spans
  they contain, and count spans per label (e.g. for the confusion matrix or as a
  plot axis).
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
- **Larger corpora.** The plot routes return every document at once. Check how
  this scales to around 100k documents, and sample or aggregate where needed.

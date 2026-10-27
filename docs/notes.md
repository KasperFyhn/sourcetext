# Notes

Notes you write in the app are saved to a JSONL file. Pass its path as
`notes_file=` to load the notes in it when the `SourceText` is created:

```python
st = SourceText(texts, prediction=preds, notes_file="notes.jsonl")
```

The file doesn't need to exist yet; it is created when the first note is written.

## Choosing the file

Notes are always saved to a file; they're never kept only in memory. Without
`notes_file=`, sourcetext looks for `sourcetext_notes.jsonl` in your working
directory and uses it if it's there. This is the app's suggested file, so notes
saved there come back when you run the same code again. Otherwise the notes field
is disabled until you click **Select notes file ...** next to it: pick a new file,
or the file you saved notes to before to continue with them (relative paths are
relative to your Python session's working directory). Once chosen, the file's name
is shown there instead; click it to switch to another file.

If you switch to a file that has a different note on a document than the one
you're already using, neither note is lost: both are kept in one note, the older first, separated by
`---`.

## File format

Each line of the file is one note:

```json
{"document_id": "42", "text_hash": "3f2a9c1e0b7d4e85", "note": "Sarcasm, not praise.", "updated_at": "2026-10-13T12:00:00+00:00"}
```

Read it back into pandas with `pd.read_json("notes.jsonl", lines=True)`.

## Matching notes to documents

Notes are matched back to documents like this:

- **With `doc_id=`**: by document ID. You're warned if a document's text has changed
  since its note was written.
- **Without `doc_id=`**: by the text itself (`text_hash`), since the default IDs are
  just row positions and change when the data is reordered or filtered. If several
  documents have exactly the same text, the note is shown on all of them.

Notes for documents that aren't in the current corpus (e.g. when you load a
subset) are kept in the file, not deleted. You're told how many there are.

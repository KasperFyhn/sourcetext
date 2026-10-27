---
name: frontend-organization
description: Principles for where UI code goes and how it is split in ui/src. Use when adding, splitting, moving or renaming React components, hooks, contexts, API calls or helpers in ui/, or when reorganizing the frontend.
---

# Frontend code organization

Principles for `ui/src/`. Apply them to new code; when touching old code that breaks them,
move it in a separate commit (see "Moves" below).

## Target layout

```
ui/src/
  main.tsx, App.tsx
  api/          # all server calls, split by resource; shared types in types.ts
    types.ts  documents.ts  plots.ts  spans.ts  notes.ts
  views/        # one folder per view, with its view-only children
    tabular/  plot/  matrix/  spans/
  document/     # the document pane (DocumentView, DocumentNotes, ...)
  fields/       # per field type: filter control + value renderer side by side
    label/  score/  span/  temporal/  text/
  common/       # components used by several views (ColorLegend, SpanBadge, ...)
  hooks/        # data-fetching and state hooks used by more than one place
  contexts/     # React contexts (NotesFileContext, ...)
  lib/          # pure .ts helpers without JSX (colors, plotting, ...)
```

## Principles

1. **One component per file**, named after the component. Exception: a small child
   component tightly bound to its parent (not exported, not used elsewhere) may stay in
   the parent's file.
   *Why:* files stay findable by name, and big multi-component files (e.g. the old
   `FieldFilters.tsx`) become hard to navigate.
2. **Group by view and by field type.** A view's folder holds the view and its
   view-only children. Field-type folders mirror the backend's field types, so a type's
   filter control and value display live together.
   *Why:* adding a view or a field type touches one folder, not a flat list.
3. **Imports go one way:** `views → document / fields / common → hooks / contexts → api / lib`.
   A view never imports from another view; anything two views need moves down to
   `common/`, `fields/` or `lib/`.
   *Why:* avoids tangles where changing one view breaks another.
4. **Fetching lives in hooks, not in components.** Only `api/` calls `fetch`; components
   get data from a hook (next to the view if only it uses it, else in `hooks/`) and mostly
   render.
   *Why:* keeps components readable and loading/error handling consistent.
5. **`api/` is split by resource, mirroring the backend route modules**, with shared
   request/response types in `api/types.ts`.
   *Why:* a backend route and its client code are easy to find from each other.
6. **Logic without JSX goes in `.ts` files** (in `lib/`, or next to its only user):
   clamping, step sizes, span aggregation, text highlighting and similar.
   *Why:* it can be unit-tested and reused without rendering anything.
7. **Shared constants have one home** (e.g. `NO_LABEL`, the named-field defaults of the plot and matrix views) in `lib/` or the
   relevant `fields/<type>/`, never exported from a component file.
   *Why:* importing a constant shouldn't pull in a component.

## Applies to both frontend and backend

- **One name per concept, from `VOCABULARY.md`.** Views, their folders and `api/`
  modules use the view names (`tabular`, `plot`, `matrix`, `spans`); routes may name
  the data shape they return (`scatter`, `strip`, `crosstab`). A new concept gets its
  name added there first. Field names stay raw in the UI (no prettified display names).
- **Size is a signal, not a rule.** A file past ~300 lines, or exporting several
  components, is a prompt to check whether it holds more than one concern.
- **Moves are separate commits** from behaviour changes, so the diff is pure moves and
  renames.
- **Docs follow the code.** A move updates paths in `CLAUDE.md` and `docs/` in the same
  change.

## Where does new UI code go?

- A new view → `views/<view>/`, plus its client calls in `api/<resource>.ts`.
- A filter or value display for a field type → `fields/<type>/`.
- A component a second view now needs → move it to `common/` (or `fields/<type>/`).
- A `useEffect` that fetches → a hook; the `fetch` itself → `api/`.
- A helper with no JSX → `lib/` or a `.ts` file next to its user.
- After adding or moving files: `npm run lint` / `npm run build` in `ui/`.

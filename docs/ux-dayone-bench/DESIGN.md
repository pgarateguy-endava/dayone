---
name: Bench Assistant Local UI
description: A practical, operator-first web interface for managing Bench onboarding and daily progress.
status: final
updated: 2026-07-20
sources:
  - ../PRODUCT_SPEC.md
  - ../BACKOFFICE_SPEC.md
  - ../BENCH_SPEC.md
  - ../ARCHITECTURE.md
  - ../../bench/webapp.py
colors:
  ink: '#1B1B25'
  paper: '#F7F6F3'
  surface: '#FFFFFF'
  line: '#E8E6E1'
  muted: '#75717A'
  accent: '#FF4A1C'
  accent-dark: '#D63A12'
  success-surface: '#E5F6EC'
  success-ink: '#14683A'
  warning-surface: '#FDF3D7'
  warning-ink: '#8A6116'
  danger-surface: '#FDE8E4'
  danger-ink: '#A52A12'
  info-surface: '#E9E7FD'
  info-ink: '#4438A8'
typography:
  body:
    fontFamily: "-apple-system, 'Segoe UI', Inter, system-ui, sans-serif"
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.5'
  heading:
    fontFamily: "-apple-system, 'Segoe UI', Inter, system-ui, sans-serif"
    fontSize: 26px
    fontWeight: '800'
    lineHeight: '1.2'
    letterSpacing: '-0.3px'
  section:
    fontFamily: "-apple-system, 'Segoe UI', Inter, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: '700'
    lineHeight: '1.3'
  label:
    fontFamily: "-apple-system, 'Segoe UI', Inter, system-ui, sans-serif"
    fontSize: 13px
    fontWeight: '600'
    lineHeight: '1.3'
  meta:
    fontFamily: "-apple-system, 'Segoe UI', Inter, system-ui, sans-serif"
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 8px
  md: 10px
  lg: 14px
  xl: 16px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 20px
  '6': 26px
  '7': 30px
  '8': 40px
components:
  page:
    background: '{colors.paper}'
    maxWidth: 1150px
    gutter: '{spacing.5}'
  navigation:
    background: '{colors.ink}'
    foreground: '#FFFFFF'
    active: '{colors.accent}'
    height: 56px
  card:
    background: '{colors.surface}'
    border: '1px solid {colors.line}'
    radius: '{rounded.lg}'
    padding: '{spacing.6}'
  primary-button:
    background: '{colors.ink}'
    foreground: '#FFFFFF'
    radius: '{rounded.sm}'
  add-button:
    background: '{colors.accent}'
    foreground: '#FFFFFF'
    radius: '{rounded.full}'
  input:
    background: '{colors.surface}'
    border: '#D7D4CD'
    focus: '{colors.accent}'
    radius: '{rounded.sm}'
  status-badge:
    radius: '{rounded.full}'
    fontSize: 12px
  dialog:
    background: '{colors.surface}'
    radius: '{rounded.xl}'
    backdrop: 'rgba(27, 27, 37, 0.5)'
---

# Bench Assistant Local UI — Design Spine

## Brand & Style

Bench Assistant is a workbench, not a celebration layer. The visual language is confident, compact,
and operational: a dark navigation bar, warm paper canvas, white work surfaces, and one orange action
accent. The interface should help a manager see risk and act quickly without feeling like an alarm
console. Dense catalog data is acceptable; hierarchy comes from spacing, headings, and status labels,
not decoration.

The system inherits the existing FastAPI/htmx implementation's visual language. This is an intentional
continuity rule: completing the UI should make the product feel more coherent, not introduce a new
brand system during the MVP.

## Colors

- **Ink** (`{colors.ink}`) anchors navigation, primary actions, and body text.
- **Paper** (`{colors.paper}`) is the page canvas and keeps tables from feeling clinical.
- **Surface** (`{colors.surface}`) contains one coherent task or catalog section.
- **Line** (`{colors.line}`) separates rows quietly; it is not a decorative border.
- **Muted** (`{colors.muted}`) is for metadata, helper text, and secondary labels only.
- **Accent** (`{colors.accent}`) is reserved for creation and the active navigation underline.
- **Accent dark** (`{colors.accent-dark}`) is used for links and destructive emphasis.
- Status surfaces and inks are semantic pairs: success, warning, danger, and informational state.
  Status colors never replace the status text.

Avoid gradients, illustrations, decorative charts, and multiple competing brand accents. A danger
state is not an opportunity for a large red panel; it is a precise warning beside the affected record.

## Typography

The system sans stack is the contract. `{typography.heading}` is used once for the page title and
rarely for a major detail title. `{typography.section}` labels cards and sections. `{typography.body}`
handles user-facing content and form values. `{typography.label}` labels inputs. `{typography.meta}`
handles email addresses, IDs, timestamps, and helper explanations.

Never use all-caps for user-facing labels, never encode hierarchy through tiny gray text alone, and do
not truncate names, statuses, or error messages when wrapping can preserve meaning.

## Layout & Spacing

Use the 4px base scale. `{spacing.6}` separates a card's content from its edge; `{spacing.8}` marks a
new page section. The page uses `{components.page.maxWidth}` with `{components.page.gutter}` gutters.

Dashboard and review pages may use grids for summary metrics, but forms remain one clear vertical
sequence. Tables are full-width within cards. On narrow viewports, tables scroll horizontally and row
actions remain reachable; the information order does not change.

## Elevation & Depth

Cards use a thin `{colors.line}` border and a restrained shadow equivalent to the existing UI. Do not
use elevation to imply workflow status. Dialogs may use a stronger shadow because they interrupt the
current surface. The backdrop darkens the page but never hides the dialog's title or action buttons.

## Shapes

Inputs and ordinary buttons use `{rounded.sm}`. Cards use `{rounded.lg}`. Dialogs use `{rounded.xl}`.
Status badges and the add action use `{rounded.full}` because their compact shape communicates a
label or a discrete creation affordance. Do not make whole cards pill-shaped.

## Components

- **Navigation:** `{components.navigation}` with a visible active link. At desktop, links remain in a
  single top row. At narrow widths, navigation wraps or collapses into a clearly labelled menu; it
  must not become an undiscoverable icon strip.
- **Card:** `{components.card}` groups one decision or one data set. Card headings align with the first
  content row and the primary action sits at the heading's right edge.
- **Primary button:** `{components.primary-button}` for save, review, update, and other committed
  actions. Its label is a verb.
- **Add button:** `{components.add-button}` opens a native dialog for new catalog records. The plus
  sign is supplemental; the text label carries the meaning.
- **Table:** headers use `{typography.meta}` with muted color and a bottom line. Actions are in the
  final column and remain visible without hover.
- **Inline edit row:** the editing row uses the surface's existing background with a subtle warm tint;
  Save and Cancel remain adjacent and keyboard reachable.
- **Dialog:** `{components.dialog}` contains one form only. The title states the entity and action;
  Cancel is always available. Destructive confirmations name the record.
- **Status badge:** `{components.status-badge}` always includes text such as `active`, `blocked`, or
  `deadline at risk`; color reinforces the meaning but never carries it alone.
- **Empty state:** one sentence explaining why the surface is empty and one next action. Avoid generic
  “No data” copy.
- **Error message:** placed beside the failed form or record, with the corrective action stated.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use one clear primary action per card | Put several equally loud buttons beside a table |
| Keep status text visible beside semantic color | Use color alone to communicate state |
| Preserve the existing dark-nav, paper-canvas language | Introduce a second visual theme for one new view |
| Keep row actions visible and keyboard reachable | Hide critical actions behind hover |
| Use confirmations for delete/archive and name the record | Use an unlabeled `×` as the only destructive affordance |
| Prefer concise operational copy | Add celebratory animations, gamification, or decorative dashboards |

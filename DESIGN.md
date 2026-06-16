# DESIGN.md — ProcedureGuard

> Design system for ProcedureGuard, an AI compliance-verification dashboard.
> Drop-in spec for AI coding agents. Format: [DESIGN.md](https://getdesign.md) (Google Stitch convention).
> Aesthetic: **cinematic control-room / cyber-industrial telemetry** — pitch-black canvas, single cyan accent, monospace data, zero decoration that doesn't carry signal.

---

## 1. Visual Theme

A dark operations console for industrial compliance inspection. The feeling is a mission-control telemetry board, not a consumer SaaS app. Every surface is near-black; color appears only where it encodes a verdict (pass / fail / unverified). Motion is restrained and purposeful — a load sweep, a pulsing live dot — never decorative bounce. The dot-grid background and gradient accent lines signal "engineered instrument," not "website."

**Mood words:** precise, authoritative, calm-under-load, instrument-grade, high-signal.

**Banned:** light/white backgrounds, AI-purple gradients, glassmorphism, drop shadows, emoji in UI, rounded "friendly" blobs, more than one accent hue.

---

## 2. Color Palette

One accent (cyan), three semantic verdict colors, everything else is a near-black neutral ramp.

| Token        | Hex       | Role |
|--------------|-----------|------|
| `--bg`       | `#07090E` | App canvas (carries the dot-grid) |
| `--s1`       | `#0C0F18` | Primary surface (cards, sidebar, panels) |
| `--s2`       | `#101420` | Raised surface / hover |
| `--s3`       | `#151A28` | Track / inset fills (progress tracks) |
| `--s4`       | `#1B2133` | Deepest inset / empty matrix cells |
| `--border`   | `#1C2336` | Default 1px border |
| `--border-2` | `#263045` | Hover / emphasis border |
| `--text`     | `#EDF1FA` | Primary text |
| `--mid`      | `#7A849E` | Secondary / body text |
| `--dim`      | `#3C4560` | Labels, eyebrows, axis ticks |
| `--accent`   | `#00CFFF` | The single brand accent — cyan. IDs, thresholds, focus. |
| `--pass`     | `#00E5A0` | Compliant / success (emerald) |
| `--fail`     | `#FF4466` | Deviation / failure (red) |
| `--warn`     | `#FFB000` | Unable to verify / hold (amber) |
| `--hold`     | `#3C4560` | Pending / neutral verdict |

**Rules**
- **One accent, locked.** Cyan is the only brand color. Verdict colors are semantic, not decorative — never use `--fail` for a non-error element.
- Tinted fills for status backgrounds use 6–12% alpha of the verdict color (e.g. `rgba(0,229,160,0.08)`), never a solid block.
- Text on a colored fill uses the same hue at higher intensity, never pure black/white.
- Gradients allowed **only** as 1px accent lines (`linear-gradient(90deg, transparent, var(--accent), transparent)`) and the brand mark. No filled gradient surfaces.

---

## 3. Typography

Two families, both IBM Plex. Sans for prose and numbers, Mono for every label, ID, metric unit, and axis tick.

```
--font: 'IBM Plex Sans', system-ui, sans-serif;
--mono: 'IBM Plex Mono', 'SF Mono', monospace;
```

Load via Google Fonts: weights `300,400,500,600,700` (Sans) and `400,500,600` (Mono).

| Use | Family | Size | Weight | Notes |
|-----|--------|------|--------|-------|
| Hero score | Sans | 96px | 700 | `letter-spacing: -0.04em`, line-height 1 |
| Metric value | Sans | 44px | 600 | `letter-spacing: -0.03em` |
| Section title | Sans | 14–17px | 600 | `letter-spacing: -0.01em` |
| Body | Sans | 12–13px | 400 | color `--mid`, line-height 1.4–1.5 |
| **Eyebrow / label** | **Mono** | 8.5–10px | 600 | `text-transform: uppercase; letter-spacing: 2–3px;` color `--dim` |
| ID / value / unit / tick | Mono | 10–12px | 500 | e.g. `RUN-2026-06-15-001`, `CONF 81%` |

**Rule:** if it is a label, status, ID, timestamp, count, or axis tick → **mono, uppercase, wide-tracked, dim**. If it is content a human reads as a sentence → sans.

---

## 4. Component Styling

**Cards / panels** — `background: var(--s1)`, `1px solid var(--border)`, `border-radius: 8px`, padding `20–28px`. Hover lifts border to `--border-2`. Many panels carry a top 1px accent gradient line via `::before`.

**Metric card** — mono uppercase label (top) → oversized sans number → thin progress track (`--s3`) with a verdict-colored fill → mono sub-caption. A 2px verdict-colored bar pinned to the bottom edge via `::after`.

**Verdict banner** — `border-left: 2px solid <verdict>`, tinted background at 6% alpha, a pulsing dot, a mono uppercase title, a sans message.

**Status badge / pill** — mono, uppercase, 8.5px, `letter-spacing 0.8px`, radius 4px, 12% alpha background of its verdict color.

**Step matrix** — 18–22px rounded squares (radius 3–4px) in a flex-wrap grid, one per inspected step, colored by verdict at 70–85% opacity. `:hover` scales to 1.3–1.4×. This is the signature component — a GitHub-contributions-style heat grid for SOP compliance.

**Mode badge (live/mock)** — pill with a `pulse` animation dot; green when live, amber when mock.

**Charts (Plotly)** — transparent paper + plot background, gridlines `#1C2336`, all fonts IBM Plex, verdict-colored series. Donut hole holds the score. No mode bar.

---

## 5. Layout Principles

- Max content width **1480px**, side padding 1.5rem.
- **Sidebar (≈190px)** — brand mark + nav + pipeline status block. Background `--s1`, right border `--border`.
- **Full-bleed top run-bar** spanning the content, with a gradient hairline on top and metadata columns separated by 1px dividers; mode badge pushed right with `margin-left: auto`.
- **Hero row:** asymmetric `1.1fr / 0.9fr` — giant score card beside the donut breakdown.
- **Metric strip:** exactly 4 equal columns.
- **Analysis row:** `1.1fr / 0.9fr` — chapter bars beside the step matrix.
- Vertical rhythm in rem (1rem / 1.5rem / 2rem); component-internal gaps in px (4 / 8 / 12 / 16).
- Section dividers: mono uppercase label + optional count badge, on a `1px solid --border` bottom rule.

---

## 6. Depth & Elevation

Flat. Depth is communicated by **surface lightness** (`--bg` → `--s1` → `--s2` → `--s3`), 1px borders, and accent hairlines — **never** by drop shadows or blur. The only "glow" permitted is a low-alpha radial on a stat corner or the sweep animation. Elevation hierarchy: canvas (darkest) < panel < raised/hover < inset track (used for fills, can be darker again).

---

## 7. Motion

Sparing and signal-bearing. Respect `prefers-reduced-motion`.

| Animation | Where | Spec |
|-----------|-------|------|
| `fade-up` | cards on mount | 0.4s ease, `translateY(8–10px)` → 0, slight stagger |
| `sweep` | hero score | a faint cyan light ray crosses once on load (3s) |
| `pulse-dot` | live badge, active verdict dots | 2–2.5s ease infinite, opacity+scale |
| border transition | card hover | `border-color 0.15s` |
| cell scale | matrix hover | `transform 0.1s`, scale 1.3–1.4 |

No spinners, no parallax, no scroll-jacking, no bounce easings.

---

## 8. Responsive Behavior

- ≥1280px: full multi-column layouts as specced.
- 768–1280px: collapse 4-col metric strip to 2 columns; hero and analysis rows stack to single column.
- <768px: everything single-column; sidebar collapses (Streamlit default); matrix cells may shrink to 14px; top-bar metadata columns wrap.
- Always declare the `<768px` fallback per component — never assume the grid handles it.

---

## 9. Agent Prompt Guide

When generating or editing UI for ProcedureGuard:

1. **Start from the tokens in §2.** Reference CSS variables, never raw hex inline (except inside Plotly configs, which can't read CSS vars — mirror the same hex there).
2. **Label test:** every label/ID/unit/tick is mono-uppercase-dim. Every sentence is sans. If you wrote a label in sans, fix it.
3. **One accent:** if you reach for a second brand color, stop — use a neutral or an existing verdict color instead.
4. **No emoji** in any rendered UI. Use the inline SVG shield mark or a verdict dot.
5. **Status = color + shape + text**, never color alone (accessibility): dot + mono label + tinted bg.
6. **Charts** inherit §4: transparent bg, `#1C2336` grid, IBM Plex fonts, verdict-colored series.
7. **Prefer the signature components** (step matrix, donut-with-score, metric strip, full-bleed run-bar) before inventing new layouts.
8. Round every displayed number. Keep CTA/labels to ≤3 words.
9. Stack (don't shadow) for depth; animate only per §7.

Reference implementation: [`scripts/08_dashboard.py`](scripts/08_dashboard.py).

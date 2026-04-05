# CSAT Design System
**CIS Controls v8.1 Assessment Tool — UI Reference**

> **IMPORTANT**: All future UI work on this application MUST reference this document. Do not hard-code colours, spacing, or typography values outside of the token definitions in `index.html`'s `:root` and `[data-theme="dark"]` blocks. Always use the CSS custom properties defined here.

---

## 1. Design Principles

| Principle | Description |
|-----------|-------------|
| **Clarity** | Information density is high; every element must earn its space. Avoid decoration that doesn't carry meaning. |
| **Consistency** | Same component, same class. Never duplicate styling rules — extend via modifier classes. |
| **Accessibility** | Colour alone is never the sole conveyor of status. All interactive elements have focus rings. |
| **Theme-aware** | Every colour MUST resolve through a CSS variable. No raw hex values in component rules. |

---

## 2. Colour Tokens

Defined on `:root` (light) and `[data-theme="dark"]` (dark). Reference by variable name, never by value.

### Brand
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--brand-primary` | `#1e3a5f` | `#1e3a5f` | Navbar, control number badges |
| `--brand-accent` | `#3b82f6` | `#58a6ff` | Links, focus rings, active buttons, safeguard IDs |

### Backgrounds
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--bg-page` | `#f0f4f8` | `#0d1117` | Body background |
| `--bg-surface` | `#ffffff` | `#161b22` | Cards, navbar, inputs |
| `--bg-surface-2` | `#f8fafc` | `#21262d` | Rows, secondary panels, filter bar inputs |
| `--bg-surface-3` | `#f1f5f9` | `#2d333b` | Hover states, description blocks, drop zone |

### Borders
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--border` | `#e2e8f0` | `#30363d` | Default borders on all surfaces |
| `--border-strong` | `#cbd5e1` | `#484f58` | Hover borders, description left-rule, drop zone |

### Text
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--text-primary` | `#0f172a` | `#f0f6fc` | Body copy, titles |
| `--text-secondary` | `#475569` | `#8b949e` | Supporting text, metadata |
| `--text-muted` | `#94a3b8` | `#6e7681` | Timestamps, labels, placeholder text |
| `--text-link` | `#3b82f6` | `#58a6ff` | Clickable elements |

### Semantic
| Token | Light | Dark | Usage |
|-------|-------|------|-------|
| `--color-success` | `#16a34a` | `#3fb950` | IG1 score, implemented status, flash saved |
| `--color-warning` | `#d97706` | `#d29922` | Partial status |
| `--color-danger` | `#dc2626` | `#f85149` | Delete hover, not-implemented |
| `--color-info` | `#2563eb` | `#58a6ff` | IG2 score, attachment accent, safeguard ID (dark) |
| `--color-purple` | `#7c3aed` | `#bc8cff` | IG3 score |

### Status Colours (Select Dropdown)
Each status has three tokens: `-bg`, `-color`, `-border`.

| Status | Light bg / color / border | Dark bg / color / border |
|--------|--------------------------|--------------------------|
| `not_assessed` | `#f8fafc` / `#64748b` / `#e2e8f0` | `#21262d` / `#8b949e` / `#30363d` |
| `not_implemented` | `#fef2f2` / `#991b1b` / `#fecaca` | `#2d1b1b` / `#f85149` / `#5a1f1f` |
| `partial` | `#fffbeb` / `#92400e` / `#fde68a` | `#2d2208` / `#d29922` / `#5a4008` |
| `implemented` | `#f0fdf4` / `#166534` / `#bbf7d0` | `#0d2818` / `#3fb950` / `#1a4d2a` |
| `not_applicable` | `#f1f5f9` / `#475569` / `#e2e8f0` | `#21262d` / `#6e7681` / `#30363d` |

---

## 3. Typography

**Font stack**: `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif`

No external font loading. System fonts only for performance and offline reliability.

| Role | Size | Weight | Element |
|------|------|--------|---------|
| Navbar brand | `0.95rem` | 700 | `.app-nav-brand` |
| Control title | `0.875rem` | 600 | `.ctrl-title` |
| Safeguard title | `0.85rem` | 400 | `.sg-title-text` |
| Body / notes | `0.77–0.78rem` | 400 | `.note-body`, `.att-link` |
| Stat value | `2rem` | 800 | `.stat-val` |
| Labels / badges | `0.6–0.72rem` | 600–700 | `.stat-label`, `.fn-badge` |
| Timestamps / muted | `0.63rem` | 400 | `.note-ts`, `.updated-lbl` |

---

## 4. Spacing & Radii

**Spacing** follows a 4px base grid. Use multiples: 4, 8, 12, 16, 20, 24px.

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Inputs, badges, notes items |
| `--radius-md` | `10px` | Cards, filter bar |
| `--radius-lg` | `14px` | Large modals (future) |
| `--radius-pill` | `999px` | Buttons, IG badges, progress bars |

---

## 5. Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)` | Cards, filter bar |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)` | Elevated surfaces (future) |

Dark mode shadows are stronger: `rgba(0,0,0,0.3)` and `rgba(0,0,0,0.2)`.

---

## 6. Components

### Navbar (`.app-nav`)
- Sticky, `z-index: 100`
- Background: `var(--navbar-bg)` — always dark (`#1e3a5f` / `#161b22`)
- Buttons: `.btn-nav` — pill shape, transparent with white border, hover fills

### Stat Cards (`.stat-card`)
- 4-column grid on ≥md, 2-column on mobile
- Stat value colour tied to semantic token (success/info/purple/primary)
- Progress track: `5px` height, `var(--bg-surface-3)` background, coloured fill

### Control Cards (`.ctrl-card`)
- Surface + border + `--shadow-sm`
- Header: flex row — `ctrl-num` badge | title | meta | score | chevron
- Chevron rotates `−90deg` when `.collapsed`
- Control number badge: navy in light, surface-3 in dark

### Safeguard Rows (`.sg-row`)
- CSS grid: `52px 1fr 170px 82px`
- Safeguard ID: `--brand-accent` (light) / `--color-info` (dark)
- Description block (`.sg-desc.open`): surface-2 bg, left border `--border-strong`

### Badges
- All badges: pill shape (`--radius-pill`), `0.6rem`, `700` weight
- Function badges: semantic light/dark pairs (see colour table above)
- IG badges: green/blue/purple in both modes
- Asset class badge (`.ac-badge`): surface-3 bg, secondary text, with border

### Status Select (`.status-select`)
- Custom chevron via `background-image` SVG
- `appearance: none` to remove native arrow
- Focus ring: `0 0 0 3px rgba(59,130,246,0.15)`
- Colour set via `.s-{status}` modifier using status tokens

### Action Buttons (`.btn-action`)
- Pill shape, `0.7rem`, full-width within their column
- Default: surface-2 bg, muted text, border
- With items (`.has-items`): accent-coloured border and text
- Hover: surface-3 bg, stronger border, primary text

### Notes Panel (`.notes-panel`)
- Hidden by default, `.open` shows it
- Note items: surface-2 bg, left border `--brand-primary` (light) / `--color-info` (dark)
- Add-note textarea: surface bg, focus ring on brand-accent
- Add button: `.btn-add-note` — pill, outline style, fills on hover

### Attachments Panel (`.att-panel`)
- Mirrors notes panel structure
- Note items left border: `--color-info`
- Drop zone: `2px dashed --border-strong`, `.over` state → accent colours

---

## 7. Dark Mode

**Implementation**: `data-theme="light|dark"` on `<html>`. Toggle via button in navbar. Preference persisted in `localStorage` key `"csat-theme"`.

**JS toggle pattern**:
```js
function toggleTheme() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  document.documentElement.dataset.theme = isDark ? 'light' : 'dark';
  localStorage.setItem('csat-theme', isDark ? 'light' : 'dark');
  document.getElementById('themeBtn').textContent = isDark ? '🌙' : '☀️';
}
// On load:
const saved = localStorage.getItem('csat-theme') || 'light';
document.documentElement.dataset.theme = saved;
```

**Control score colours** (set dynamically via JS `style.color`): These use absolute hex values that work in both modes: `#22c55e` (green), `#f59e0b` (amber), `#ef4444` (red), `#94a3b8` (grey).

---

## 8. Control Score Thresholds

Applied in `updateControlScores()`:
- `≥ 80%` → `#22c55e` (green)
- `≥ 50%` → `#f59e0b` (amber)
- `> 0%` → `#ef4444` (red)
- `0%` → `#94a3b8` (grey/not started)

---

## 9. Future Extension Rules

- **New status values**: Add tokens to both `:root` and `[data-theme="dark"]`. Add `.s-{value}` CSS class. Add `<option>` to select. Add to `valid_statuses` in `app.py`.
- **New badge types**: Follow existing `.fn-{name}` pattern — light and dark variants required.
- **New panels** (e.g. due dates): Follow `.notes-panel` / `.att-panel` pattern — hidden by default, toggled with `.open`, button uses `.btn-action`.
- **New cards/surfaces**: Use `--bg-surface`, `--border`, `--shadow-sm`. Never hardcode white or a grey hex.

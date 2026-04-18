# LibreVigilant Design System — Sentinel Indigo
**LibreVigilant — CIS Controls v8.1 Assessment Tool — UI Reference**
**Source:** Stitch project `6004159817817914172`, design system `assets/307ee8da7c864dbfbf4b59612407b55a` (v1)

> **IMPORTANT**: All future UI work on this application MUST reference this document. Do not hard-code colours, spacing, or typography values outside of the token definitions in `index.html`'s `:root` and `[data-theme="dark"]` blocks. Always use the CSS custom properties defined here.

---

## 1. Design Philosophy — The Sovereign Interface

This system rejects generic "cyberpunk" aesthetics in favour of a calm, authoritative, editorial interface. Key principles:

| Principle | Rule |
|-----------|------|
| **No-Line Rule** | 1px solid borders for sectioning are **prohibited**. Use background colour shifts to define boundaries. |
| **Tonal Layering** | Surfaces are physical sheets of matte material; depth is expressed through background tiers, not shadows. |
| **Negative Pressure** | Use generous vertical spacing (80px+ between major sections) to direct the eye toward critical data. |
| **Glass Headers** | Floating headers/sidebars: `background` at 0.8 opacity + `backdrop-filter: blur(20px)`. |
| **Machined CTAs** | Primary buttons use a linear gradient from `--primary` → `--primary-container`, not a flat fill. |
| **No Glow** | Never use neon glow effects. Highlight with solid `--primary` lines at high contrast. |
| **Thin Icons** | 1.5pt stroke-weight icons only. No varying line weights. |

---

## 2. Colour Tokens

Both modes use the same CSS custom property names. `:root` defines **dark** (primary); `[data-theme="light"]` overrides to the light palette. Dark values come directly from the Stitch Sentinel Indigo palette; light values are derived from the Stitch `_fixed` / `inverse_*` tokens using Material Design inversion.

### Surface Hierarchy

| CSS Custom Property | Dark | Light | Level |
|---------------------|------|-------|-------|
| `--surface-base` | `#131314` | `#FAFAFB` | 0 — Page base |
| `--surface-lowest` | `#0E0E0F` | `#F2F2F3` | Sub-base |
| `--surface-low` | `#1C1B1C` | `#EEEEF0` | 1 — Section backgrounds |
| `--surface` | `#201F20` | `#FFFFFF` | 2 — Cards |
| `--surface-high` | `#2A2A2B` | `#EEEEFF` | Hover states |
| `--surface-highest` | `#353436` | `#E6E6FF` | Inputs, chips |
| `--surface-bright` | `#3A393A` | `#FFFFFF` | 3 — Popovers, modals |
| `--surface-tint` | `#C0C1FF` | `#494BD6` | Focus ghost borders |
| `--surface-variant` | `#353436` | `#E5E2E3` | Alternate containers |

### Primary (Indigo)

| CSS Custom Property | Stitch source | Dark | Light |
|---------------------|--------------|------|-------|
| `--primary` | `primary` / `inverse_primary` | `#C0C1FF` | `#494BD6` |
| `--primary-container` | `primary_container` / `primary_fixed` | `#5255E0` | `#E1E0FF` |
| `--on-primary` | `on_primary` | `#1000A9` | `#FFFFFF` |
| `--on-primary-container` | `on_primary_container` / `on_primary_fixed` | `#E6E4FF` | `#07006C` |
| `--inverse-primary` | `inverse_primary` / `primary` | `#494BD6` | `#C0C1FF` |

### Secondary (Slate)

| CSS Custom Property | Dark | Light |
|---------------------|------|-------|
| `--secondary` | `#B9C8DE` | `#39485A` |
| `--secondary-container` | `#39485A` | `#D4E4FA` |
| `--on-secondary` | `#233143` | `#FFFFFF` |
| `--on-secondary-container` | `#A7B6CC` | `#0D1C2D` |

### Tertiary (Emerald)

| CSS Custom Property | Dark | Light |
|---------------------|------|-------|
| `--tertiary` | `#4EDEA3` | `#007650` |
| `--tertiary-container` | `#007650` | `#6FFBBE` |
| `--on-tertiary` | `#003824` | `#FFFFFF` |
| `--on-tertiary-container` | `#77FFC2` | `#002113` |

### Error / Semantic

| CSS Custom Property | Dark | Light | Usage |
|---------------------|------|-------|-------|
| `--error` | `#FFB4AB` | `#BA1A1A` | Not-implemented, delete hover |
| `--error-container` | `#93000A` | `#FFDAD6` | Error backgrounds |
| `--on-error` | `#690005` | `#FFFFFF` | Text on error surfaces |
| `--color-success` | `#4EDEA3` | `#007650` | Implemented, IG1, healthy radar |
| `--color-warning` | `#D29922` | `#B45309` | Partial status |
| `--color-danger` | `#FFB4AB` | `#BA1A1A` | Not-implemented status |

### Text

| CSS Custom Property | Dark | Light |
|---------------------|------|-------|
| `--on-surface` | `#E5E2E3` | `#1A1A1C` |
| `--on-surface-variant` | `#C7C4D6` | `#44424F` |
| `--outline` | `#918F9F` | `#76737F` |
| `--outline-variant` | `#464554` | `#C6C3D3` |

### Outline / Ghost Border

The **Ghost Border** is the only permitted border style when a border is required for accessibility (e.g., input focus):
- Token: `--outline-variant`
- Opacity: 20%
- Weight: 1px

### IG Level Colours (chips)

Desaturated in dark mode, deeper in light mode for contrast:

| Level | CSS Property | Dark | Light |
|-------|-------------|------|-------|
| IG1 | `--ig1-color` | `#A5B4FC` | `#4338CA` |
| IG2 | `--ig2-color` | `#93C5FD` | `#1D4ED8` |
| IG3 | `--ig3-color` | `#C4B5FD` | `#6D28D9` |

### Status Colours

**Dark mode:**

| Status | bg | color |
|--------|-----|-------|
| `not_assessed` | `#2A2A2B` | `#C7C4D6` |
| `not_implemented` | `#2D1B1B` | `#FFB4AB` |
| `partial` | `#2D2208` | `#D29922` |
| `implemented` | `#0D2818` | `#4EDEA3` |
| `not_applicable` | `#1C1B1C` | `#918F9F` |

**Light mode:**

| Status | bg | color |
|--------|-----|-------|
| `not_assessed` | `#EEEEF0` | `#44424F` |
| `not_implemented` | `#FFDAD6` | `#BA1A1A` |
| `partial` | `#FFF3D6` | `#B45309` |
| `implemented` | `#D4F8EC` | `#007650` |
| `not_applicable` | `#F2F2F3` | `#76737F` |

### CSS Variable Blocks

Implement these in `index.html`:

```css
:root, [data-theme="dark"] {
  --surface-base: #131314;
  --surface-lowest: #0E0E0F;
  --surface-low: #1C1B1C;
  --surface: #201F20;
  --surface-high: #2A2A2B;
  --surface-highest: #353436;
  --surface-bright: #3A393A;
  --surface-tint: #C0C1FF;
  --surface-variant: #353436;

  --primary: #C0C1FF;
  --primary-container: #5255E0;
  --on-primary: #1000A9;
  --on-primary-container: #E6E4FF;
  --inverse-primary: #494BD6;

  --secondary: #B9C8DE;
  --secondary-container: #39485A;
  --on-secondary: #233143;
  --on-secondary-container: #A7B6CC;

  --tertiary: #4EDEA3;
  --tertiary-container: #007650;
  --on-tertiary: #003824;
  --on-tertiary-container: #77FFC2;

  --error: #FFB4AB;
  --error-container: #93000A;
  --on-error: #690005;

  --on-surface: #E5E2E3;
  --on-surface-variant: #C7C4D6;
  --outline: #918F9F;
  --outline-variant: #464554;

  --color-success: #4EDEA3;
  --color-warning: #D29922;
  --color-danger: #FFB4AB;

  --ig1-color: #A5B4FC;
  --ig2-color: #93C5FD;
  --ig3-color: #C4B5FD;

  --shadow-sm: 0 4px 24px -1px rgba(14,14,15,0.2);
  --shadow-md: 0 8px 40px -2px rgba(14,14,15,0.3);
}

[data-theme="light"] {
  --surface-base: #FAFAFB;
  --surface-lowest: #F2F2F3;
  --surface-low: #EEEEF0;
  --surface: #FFFFFF;
  --surface-high: #EEEEFF;
  --surface-highest: #E6E6FF;
  --surface-bright: #FFFFFF;
  --surface-tint: #494BD6;
  --surface-variant: #E5E2E3;

  --primary: #494BD6;
  --primary-container: #E1E0FF;
  --on-primary: #FFFFFF;
  --on-primary-container: #07006C;
  --inverse-primary: #C0C1FF;

  --secondary: #39485A;
  --secondary-container: #D4E4FA;
  --on-secondary: #FFFFFF;
  --on-secondary-container: #0D1C2D;

  --tertiary: #007650;
  --tertiary-container: #6FFBBE;
  --on-tertiary: #FFFFFF;
  --on-tertiary-container: #002113;

  --error: #BA1A1A;
  --error-container: #FFDAD6;
  --on-error: #FFFFFF;

  --on-surface: #1A1A1C;
  --on-surface-variant: #44424F;
  --outline: #76737F;
  --outline-variant: #C6C3D3;

  --color-success: #007650;
  --color-warning: #B45309;
  --color-danger: #BA1A1A;

  --ig1-color: #4338CA;
  --ig2-color: #1D4ED8;
  --ig3-color: #6D28D9;

  --shadow-sm: 0 4px 24px -1px rgba(10,10,11,0.08);
  --shadow-md: 0 8px 40px -2px rgba(10,10,11,0.12);
}

---

## 3. Typography — The Authoritative Voice

Two-typeface strategy: **Manrope** for display/editorial numbers, **Inter** for technical body text.

Load via Google Fonts:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">
```

### Type Scale

| Role | Token | Font | Size | Weight | Letter-spacing | Usage |
|------|-------|------|------|--------|----------------|-------|
| Display | `display-lg` | Manrope | `3.5rem` | 800 | `-0.02em` | Hero metrics, total score |
| Headline | `headline-sm` | Manrope | `1.5rem` | 700 | `-0.01em` | Major assessment categories |
| Title | `title-md` | Inter | `1.125rem` | 600 | `0.01em` | Card titles, navigation |
| Body | `body-md` | Inter | `0.875rem` | 400 | `0.02em` | Safeguard descriptions, notes |
| Label | `label-sm` | Inter | `0.6875rem` | 600 | `0.08em` | **UPPERCASE.** Technical metadata, badges |

CSS custom properties:
```css
--font-display: 'Manrope', sans-serif;
--font-body: 'Inter', sans-serif;
```

---

## 4. Spacing & Radii

Spacing scale multiplier: `2` (generous). Base unit: `8px`.

Preferred vertical section gap: `80px+` for major sections.

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | `6px` | Chips, badges, small inputs |
| `--radius-md` | `12px` (xl) | All primary cards and containers |
| `--radius-lg` | `16px` | Modals, popovers |
| `--radius-pill` | `999px` | Buttons, IG chips, progress bars |

---

## 5. Elevation — Spectral Elevation

Never use heavy drop shadows. Use **Spectral Elevation** (ambient occlusion style):

| Token | Value | Usage |
|-------|-------|-------|
| Token | Dark | Light | Usage |
|-------|------|-------|-------|
| `--shadow-sm` | `rgba(14,14,15,0.2)` | `rgba(10,10,11,0.08)` | Cards, containers |
| `--shadow-md` | `rgba(14,14,15,0.3)` | `rgba(10,10,11,0.12)` | Elevated popovers |

Shadow alpha is reduced in light mode — the surface colour shift carries more of the depth work. Both are defined in the CSS variable blocks in section 2.

---

## 6. Components

### Surface Nesting Rule
Never use borders to divide sections. Shift background tokens:
- Page → `--surface-base` (`#131314`)
- Sections → `--surface-low` (`#1C1B1C`)
- Cards → `--surface` (`#201F20`)
- Hover → `--surface-high` (`#2A2A2B`)
- Popovers → `--surface-bright` (`#3A393A`)

### Navbar (`.app-nav`)
- Sticky, `z-index: 100`
- Background: `--surface-base` at 0.8 opacity + `backdrop-filter: blur(20px)` (Glass Rule)
- No bottom border — the shift to page background is the boundary

### Stat Cards (`.stat-card`)
- Background: `--surface` (`#201F20`)
- Radius: `--radius-md` (12px)
- Shadow: `--shadow-sm`
- Stat value font: `--font-display` (Manrope), `display-lg` scale
- Stat value colours: success/info/tertiary/primary tokens

### Radar Chart
- Healthy metrics: `--tertiary` (`#4EDEA3`)
- Vulnerabilities/low scores: `--error` (`#FFB4AB`)
- Grid lines: `--outline-variant` at 10% opacity

### Control Cards (`.ctrl-card`)
- Background: `--surface` (`#201F20`)
- No border — use surface colour shift from page
- Radius: `--radius-md` (12px)
- Chevron rotates `−90deg` when `.collapsed`

### Safeguard Rows (`.sg-row`)
- CSS grid: `52px 1fr 170px 82px`
- Hover: shift background to `--surface-high`
- No row dividers (No-Line Rule)
- Safeguard ID: `--primary` (`#C0C1FF`)

### Buttons
- **Primary:** `background: linear-gradient(135deg, var(--primary), var(--primary-container))`, `--radius-pill`, text `--on-primary-container`
- **Secondary:** No background, 1px `--outline-variant` at 20% opacity, `--radius-pill`
- **Tertiary:** No border, no background, `--primary` text colour, `label-sm` typography

### Inputs & Selectors
- Base: `background: var(--surface-highest)`, no border
- Focus: 1px Ghost Border using `--surface-tint` at 20% opacity
- Radius: `--radius-sm`

### Badges & Chips
- Background: `--secondary-container` (`#39485A`)
- Text: `label-sm` (Inter, 0.6875rem, uppercase, 0.08em spacing)
- Radius: `--radius-sm`
- IG level chips: fixed colours (`--ig1-color`, `--ig2-color`, `--ig3-color`), desaturated

### Notes Panel (`.notes-panel`) / Attachments Panel (`.att-panel`)
- Hidden by default, `.open` shows it
- Background: `--surface-low`
- Item left accent: `--primary`
- No dividers between items — use `16px` vertical gap

---

## 7. Dark / Light Mode

**Implementation**: `data-theme="light|dark"` on `<html>`. Preference persisted in `localStorage["librevig-theme"]`.

`:root` and `[data-theme="dark"]` both carry the dark palette. `[data-theme="light"]` overrides every token. All component styles use only CSS custom properties — no theme-specific selectors in component rules.

**JS toggle pattern** (unchanged):
```js
function toggleTheme() {
  const isDark = document.documentElement.dataset.theme === 'dark';
  document.documentElement.dataset.theme = isDark ? 'light' : 'dark';
  localStorage.setItem('librevig-theme', isDark ? 'light' : 'dark');
  document.getElementById('themeBtn').textContent = isDark ? '🌙' : '☀️';
}
const saved = localStorage.getItem('librevig-theme') || 'dark';
document.documentElement.dataset.theme = saved;
```

### Surface Nesting — both modes

| Level | Dark | Light |
|-------|------|-------|
| Page base | `#131314` | `#FAFAFB` |
| Sections | `#1C1B1C` | `#EEEEF0` |
| Cards | `#201F20` | `#FFFFFF` |
| Hover | `#2A2A2B` | `#EEEEFF` |
| Popovers | `#3A393A` | `#FFFFFF` |

---

## 8. Control Score Thresholds

Applied in `updateControlScores()` using CSS custom properties (resolves correctly in both modes):
- `≥ 80%` → `var(--color-success)` — healthy
- `≥ 50%` → `var(--color-warning)` — partial
- `> 0%` → `var(--color-danger)` — at risk
- `0%` → `var(--outline)` — not started

---

## 9. Extension Rules

- **New status values**: Add CSS tokens + `.s-{value}` class. Add `<option>`. Add to `valid_statuses` in `app.py`.
- **New badge types**: Follow `.fn-{name}` pattern using `--secondary-container` bg + `label-sm` text.
- **New surfaces**: Use `--surface` → `--surface-bright` tier; never hardcode hex values.
- **New panels**: Follow `.notes-panel` pattern — hidden default, `.open` toggle, `--surface-low` bg, no dividers.

# UI/UX Improvements

## Summary

LibreVigilant is a server-rendered Flask/Jinja2 compliance tracker built on a well-documented design system ("Sentinel Indigo"). The token foundation in `base.html` is genuinely strong — comprehensive light/dark parity, `color-mix()` for derived tints, glass navbar, and persisted theme/sidebar state. The system is in good shape conceptually.

However, the recent refactor from a single `index.html` monolith into `base.html` + child templates has left **consistency debt**: the old monolith is now dead code, several CSS custom properties referenced by child templates are never defined, and the IG/status/function colour sets are copy-pasted into four templates instead of living in `:root`. The left sidebar works but has a broken collapsed state and conflates the assessment list with per-project navigation.

This review weights the two requested areas most heavily: **design system consistency** and **sidebar layout**.

---

## Critical Issues

### Issue: `index.html` is dead code masquerading as the primary template
**Current State**: `templates/index.html` (1,312 lines) carries a full `<!DOCTYPE>`, its own complete `:root` / `[data-theme="light"]` token blocks, its own navbar, and duplicate component CSS. It is **not referenced by any `render_template()` call** in `app.py` — every live route renders `base.html`-extending children (`home.html`, `assessment.html`, `risk_register.html`, etc.).
**Problem**: This is the single biggest threat to design-system consistency. `CLAUDE.md` still describes `index.html` as "Entire UI: ... (~1200 lines)", so a future editor (human or AI) will almost certainly edit the wrong file, change tokens there, and see no effect — or worse, reintroduce it. It also duplicates the entire token set, guaranteeing drift.
**Recommendation**: Delete `templates/index.html`, and update the Key Files table in `CLAUDE.md` to point at `base.html` (tokens + layout) and the child templates. If any of its markup is still wanted, port it into a `base.html` child first.
**Impact**: Removes ~1,300 lines of drift-prone duplication; makes "where do I edit the UI" unambiguous.
**Implementation Notes**: Confirm with `grep -rn index.html app.py` (currently returns nothing). Safe to remove.

### Issue: Undefined CSS variables (`--surface-1`, `--surface-2`, `--surface-3`) break audit panels
**Current State**: `base.html` defines legacy aliases `--bg-surface`, `--bg-surface-2`, `--bg-surface-3` — but **not** `--surface-1/2/3`. Yet those exact names are used:
- `assessment.html:430` `background: var(--surface-2)`, `:436` `var(--surface-3)`, `:465` `var(--surface-2)`, `:470` `var(--surface-1)`
- `risk_register.html:580` `background:var(--surface-2)`, `:586` `var(--surface-2)`, `:587`/`:589` `var(--surface-1)`
**Problem**: `var(--undefined)` with no fallback resolves to an invalid value, so these elements (the audit-log toggle header and the pagination Prev/Next buttons) render with **no background** — transparent against the page. This is a real visual bug hiding in plain sight, and it only affects the audit/history UI so it's easy to miss in casual testing.
**Recommendation**: Replace with real tokens — `--surface-low` (sections) / `--surface-high` (hover) / `--surface` (controls) per the Surface Nesting rule. E.g. audit header `var(--surface-low)`, hover `var(--surface-high)`, buttons `var(--surface)`. Alternatively add the three aliases to `:root`, but mapping to real tokens is cleaner.
**Impact**: Audit panels and pagination regain their intended surface depth in both themes.
**Implementation Notes**: Several of these are in inline `style="..."` attributes (see "inline styles" finding below); fixing them is a good moment to lift them into the stylesheet.

---

## High Priority Improvements

### Issue: IG / status / function colours are duplicated across 4 templates instead of being tokens
**Current State**: `--ig1-color`/`--ig2-color`/`--ig3-color` are re-declared (with full light + dark blocks) in `index.html`, `assessment.html`, `risk_register.html`, and `compare.html`. Status classes (`.s-implemented` etc.) are re-declared in three templates; `.fn-Govern…` function badges in two. `base.html`'s `:root` defines colours only up to `--color-danger` and omits the IG set entirely — even though `DESIGN_SYSTEM.md` §2 lists `--ig*-color` as belonging in `:root`.
**Problem**: The same palette living in 4 places is exactly how a "design system" silently fractures — a tweak to IG2 in one screen won't propagate, and the four copies will diverge. The design doc's mandate ("define tokens once in the `:root` block") is not actually being followed.
**Recommendation**: Promote the IG colours, the five status `bg`/`color` pairs, and the six `fn-*` function-badge colours into `base.html`'s `:root` and `[data-theme="light"]` blocks as tokens (e.g. `--status-implemented-bg`, `--status-implemented-fg`, `--fn-govern-bg`…). Then reduce each child template's CSS to class rules that *reference* the tokens. Delete the duplicate `[data-theme="light"]` override blocks from the children.
**Impact**: One source of truth; ~150 lines of duplication removed; future palette changes are one-line edits.

### Issue: Collapsed sidebar shows nothing — no icon rail
**Current State**: `base.html:380-384` hides `.sidebar-title`, `.project-section`, **and** `.sidebar-footer` when `data-sidebar-collapsed="true"`. The collapsed grid column is `52px`.
**Problem**: Collapsing the sidebar produces a 52px-wide empty strip with only the expand chevron — every project, assessment, and action disappears. A collapse control that hides 100% of the content provides no value over just navigating away; users lose all context and orientation. Standard collapsed-rail patterns keep icon affordances.
**Recommendation**: Either (a) implement a real icon rail — show a per-project initial/icon and an assessment-count dot in the 52px column, with hover/click revealing a flyout; or (b) if a rail is out of scope, drop the collapse feature and keep the sidebar fixed. Half-implementing collapse is worse than not having it.
**Impact**: Collapse becomes a usable space-saver instead of a dead toggle.

### Issue: Sidebar conflates the assessment list with per-project navigation
**Current State**: Inside each project, the assessments render as `.asm-link` rows, immediately followed by **Risk Register**, **Compare**, and **Members** — styled with the *same* `.asm-link` class and the same indentation, distinguished only by a leading geometric glyph (`■ ▲ ☉`).
**Problem**: A user scanning the list cannot tell their assessments apart from project-level tools — "Risk Register" looks like it could be an assessment named "Risk Register". The information architecture mixes two object types (assessment instances vs. project views) at the same visual level. This is the core reason the sidebar "feels suboptimal."
**Recommendation**: Separate the two groups visually. Keep assessments as the primary list, then a small spacer and an uppercase `label-sm` sub-heading ("Project tools") above Risk Register / Compare / Members, or give the tools a distinct treatment (e.g. lighter weight, consistent leading icons, slightly different indent). The "+ New assessment" affordance should sit with the assessment list, not below the tools.
**Impact**: Clear separation of "what I'm assessing" from "how I view the project"; faster scanning.

### Issue: No responsive breakpoint on the app shell
**Current State**: `.shell { grid-template-columns: 260px 1fr }` (`base.html:328`) has no media query. Content templates have content-level breakpoints (`assessment.html:112`, `compare.html:75`) but the shell itself never collapses.
**Problem**: On a phone or narrow window the sidebar permanently consumes 260px of a ~375px viewport, leaving the assessment grid (`52px 1fr 170px 82px`) badly cramped or overflowing. There is no off-canvas/drawer pattern.
**Recommendation**: Add `@media (max-width: 768px)` to collapse the shell to a single column with the sidebar as an overlay drawer toggled from the navbar (reuse the existing collapse state machine). At minimum, auto-collapse the sidebar below the breakpoint.
**Impact**: Usable on tablets/phones; the assessment table stops overflowing.

---

## Medium Priority Enhancements

### Issue: `base.html` itself hardcodes colours, violating its own rule
**Current State**: Despite the "never hardcode hex" mandate, `base.html` hardcodes `color: #E5E2E3` (`:163`, `:187`), `rgba(200,195,211,0.2)` / `rgba(192,193,255,…)` / `#fff` in `.btn-nav` (`:185,:196`), and `.delete-project-btn:hover { color: #FFB4AB }` (`:572`). The filter-select dropdown arrow SVG hardcodes `fill='%2394a3b8'` (`:669`).
**Problem**: Two of these are functional bugs, not just style nits:
- `#FFB4AB` is the **dark-theme** error colour. On the light theme, the Delete-project hover turns a pale pink (`#FFB4AB` on white) instead of the intended strong `--color-danger` (`#BA1A1A`) — low contrast and off-brand for a destructive action.
- The `#94a3b8` dropdown arrow is a slate that matches neither palette and won't invert between themes.
**Recommendation**: Use `var(--color-danger)` for the delete hover. For the navbar (which is intentionally dark in both themes via `--navbar-bg`), introduce explicit `--on-navbar` / `--on-navbar-muted` tokens rather than literal hex. Recolour the select arrow via `currentColor` or a token-driven background, or use a CSS triangle/mask so it follows `--on-surface-variant`.
**Impact**: Destructive action reads as dangerous in both themes; dropdown chevrons track the theme.

### Issue: Off-token "Tailwind-ish" colours in risk register and function badges
**Current State**: `.rr-resolved-badge` uses `#fef3c7`/`#92400e` (light) and `#451a03`/`#fcd34d` (dark) — amber values not in the palette (`risk_register.html:355-365`). `.fn-Respond`/`.fn-Recover` use `#FBA06B`/`#7DD3FC` (dark) and `#FFEDD5`/`#9A3412`/`#CFFAFE`/`#155E75` (light) (`assessment.html:268-275`) — oranges/cyans absent from the documented tokens.
**Problem**: These introduce hues outside Sentinel Indigo's success/warning/danger/secondary/tertiary system. The resolved-badge in particular duplicates "warning" semantics with a different amber than `--color-warning`.
**Recommendation**: Map the resolved badge to `--color-warning` / `--surface-highest`. The six CIS function colours are a legitimate categorical scale not yet in the system — formalize them as `--fn-*` tokens in `base.html` and add them to `DESIGN_SYSTEM.md` §6 so they're sanctioned rather than ad-hoc.
**Impact**: Brings stray colours under the token system or documents them as a real extension.

### Issue: Destructive "Delete project" has weak affordance and placement
**Current State**: "Delete project" is a borderless text button (`base.html:559`) indented under "+ New assessment", muted grey at 0.6 opacity until hover.
**Problem**: A permanent, cascade-deleting action sits one line below a routine creation action with almost no visual separation. The native `confirm()` is the only guard. Easy to misclick; doesn't read as dangerous at rest.
**Recommendation**: Move project-destructive actions out of the always-visible list — e.g. into a project context menu (⋯) or the Members/settings page. If it stays inline, separate it with spacing and give it persistent (not hover-only) danger styling, and consider a type-to-confirm for cascade deletes.
**Impact**: Reduces accidental data loss; matches the gravity of the action.

### Issue: Accessibility gaps
**Current State**: aria attributes appear in only 4 templates (mostly a single use each). The sidebar nav links lead with bare numeric-entity glyphs (`&#9632;` ■, `&#9651;` ▲, `&#9737;` ☉); `importAsmSelect` (`risk_register.html:396`) has no associated label; there is no skip-to-content link; focus styling exists only for inputs (`base.html:266`), not for buttons/links generally.
**Problem**: Screen readers announce the geometric glyphs literally ("black square Risk Register"). The unlabeled select is ambiguous out of context. Keyboard users get inconsistent focus feedback. The decorative glyphs also violate the design system's "thin 1.5pt stroke icons" rule.
**Recommendation**: Replace entity glyphs with proper inline SVG icons (1.5pt stroke) marked `aria-hidden="true"`, or remove them; wrap the sidebar in `<nav aria-label="Workspace">`; add a `<label>`/`aria-label` to the import select; add a global `:focus-visible` ring using `--surface-tint`; add a skip link before the navbar.
**Impact**: Usable with assistive tech and keyboard; icons align with the design language.

### Issue: Active-nav state is too subtle, especially in light mode
**Current State**: `.asm-link[data-active="true"]` uses `background: color-mix(in srgb, var(--primary-container) 30%, transparent)` with no accent bar.
**Problem**: At 30% mix the active highlight is faint; in light mode `--primary-container` is already a pale `#E1E0FF`, so the active row barely separates from hover. The design system calls for "solid `--primary` lines at high contrast" and primary left-accents for panels — neither is used here.
**Recommendation**: Add a 3px `--primary` left accent bar to the active link and bump the background mix (or use `--surface-high`). This also reinforces hierarchy once tools are separated from assessments.
**Impact**: Users can instantly see which assessment/view is current.

---

## Low Priority Suggestions

- **Inline styles in `risk_register.html` (30 occurrences) and `assessment.html` (10).** The audit panel especially is built almost entirely from long `style="..."` strings (`risk_register.html:580-589`), which is where the undefined-variable bug hides. Lift these into the `extra_styles` block as classes — easier to keep on-token and to maintain.
- **`btn-primary` gradient deviates from spec.** `DESIGN_SYSTEM.md` §6 specifies `linear-gradient(135deg, var(--primary), var(--primary-container))`; `base.html:284` implements `var(--primary-container), var(--inverse-primary)`. Reconcile the doc and the code so the "Machined CTA" is consistent.
- **No `prefers-reduced-motion` support.** Theme/grid/transform transitions ignore the user setting. Wrap non-essential transitions in `@media (prefers-reduced-motion: no-preference)`.
- **No project/assessment search.** As projects accumulate, the sidebar becomes a long flat scroll. A filter input at the top of the workspace list would scale better.
- **Sidebar `border-right: 1px solid` (`base.html:340`)** technically breaks the design system's "No-Line Rule" (sectioning via background shift, not borders). The surface shift from `--surface-lowest` to the page already implies the boundary; consider dropping the border.

## Positive Observations

- **Token architecture is genuinely good** where it's centralized — full light/dark parity, `color-mix()` for derived tints (lifecycle badges, active states), and semantic naming. The foundation is worth protecting from the duplication noted above.
- **Glass navbar** is implemented exactly to spec (`color-mix` 80% + `backdrop-filter: blur(20px)`), with a sensible cross-browser `-webkit-` fallback.
- **State persistence is thoughtful** — theme, sidebar collapse, and per-project collapse all persist via `localStorage`, with the saved theme applied before paint to avoid a flash.
- **Truncation and overflow handling** in the sidebar (`text-overflow: ellipsis` on names, `flex-shrink: 0` on badges) is correct and prevents layout breakage from long names.
- **Lifecycle badges** are clear, consistently colour-coded, and reuse tokens via `color-mix` rather than hardcoding.
- **Server-side rendering discipline** is maintained — interactivity stays in small, focused scripts and the rendering stays in Jinja, per the architecture guidelines.

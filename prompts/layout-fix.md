# Layout and styling fix (fix/desktop-layout)

## Prompt

Read PLAN.md (section 6, Design) and CLAUDE.md. Fix the layout and styling. The app is mobile-first but must also look clean on desktop.

Problems I found on the workouts page:
1. The Search button renders as a huge half-pill shape and squeezes the search input so the placeholder is cut off ("Sear"). Fix: search input and a normal-size Search button on one row, input taking the remaining width.
2. On desktop, the filters sit in a cramped column beside the search. Put them in a tidy row BELOW the search bar: Type, Sort, From, To, then Apply and Clear. On mobile they stack and stay behind the "Filters" toggle.
3. Buttons are default blue. Use the accent color #F26B1D from PLAN.md for primary buttons (New workout, Search, Apply, Save) consistently, with a subtle secondary style for Clear/Cancel. Make sure text on orange buttons is readable.
4. Make sure the From/To date fields start EMPTY and only filter when I fill them in.

Across the whole app (workouts list, starred, new/edit workout, detail, login, sign up):
- Center content in a max-width container (about 960px) on desktop with comfortable side padding; full width with 16px gutters on phones.
- Consistent spacing, button sizes, and border radius; no squashed or oversized controls.
- No horizontal scrolling at any width.
- Check it at 375px (phone), 768px (tablet), and 1280px (desktop) and fix anything that breaks.

Also: confirm validation still rejects a run with 0 or blank distance. If a 0-distance run can be saved, fix it and add a test.

Save this prompt to prompts/layout-fix.md with a summary. Run the tests, then commit to this branch. Don't push to main.

## Summary of what was fixed

**Root causes**
- *Half-pill Search button / cramped filters:* the search `<form>` had `role="search"`, which Pico styles as a joined inline-flex button group. The whole form (search row, filters, status) was laid out side by side, and `input[type=search]` got Pico's pill radius. Now the landmark is a `<search>` element, which Pico leaves alone, and the layout is our own.
- *Blue buttons:* Pico 2 sets its colors on `:root:not([data-theme=dark])`, which outranks a plain `:root`, so the old orange override never applied. The theme now uses selectors of equal weight placed after Pico, so the overrides win in both light and dark mode.
- *Oversized everything on desktop:* Pico grows the root font size up to 125% on wide screens, and every rem with it. Pinned to 100%.

**Changes** (mostly `app/templates/base.html` CSS, plus small template edits)
- **Theme (PLAN.md §6):** primary buttons are #F26B1D with **charcoal #1F2328 text** (5.2:1 contrast; white on this orange is only 3.0:1 and fails WCAG AA), with a lighter orange on hover. In light mode the background is off-white #FAFAF7 with charcoal text, and links use a darker orange #B4490C (5.2:1) so they stay readable. Dark mode follows the phone and uses the bright accent.
- **Secondary style:** Clear, Cancel, Delete, "+ Add set" and the remove-set ✕ all share one subtle outlined, neutral style.
- **Frame:** `.container` is at most 960px, with 16px gutters on phones and 24px from 768px up. Forms and the detail page use a 40rem column, and login/sign-up sit in a centered 26rem card.
- **Controls:** one height (2.75rem), one radius (0.5rem), consistent padding. Save and Cancel now sit side by side at equal height. Link-buttons center their text.
- **Search bar** (`workouts/_search.html`): row 1 is the search input (fills the width) plus a normal Search button. Below it come Type, Sort, From, To, Apply, Clear:
  - **phone:** a 2-column grid behind a "Filters ▾" toggle. It's a CSS-only checkbox toggle with no name, so it's never sent, and it starts open when a filter is active.
  - **tablet (768px+):** the four fields on one row, with Apply and Clear right-aligned underneath.
  - **desktop (1024px+):** everything on one row.
  - Clear is now always present as a secondary button. From/To render empty unless the URL sets them, and an empty date never filters. A small script leaves empty fields and the default sort out of the URL, so links stay short (`/?q=squat`).
- **Cards:** one column on phones, an auto-fill grid (about 17rem cards) from 768px up. Long titles wrap instead of overflowing.
- **Dark mode:** cards and flash messages had a white background with light text. Card surfaces are now reset for dark mode.

**Checked** by rendering every page (list, filtered list, no matches, empty list, Starred, new, new with errors, edit, detail, delete confirm, login, login error, sign up) with sample data, then screenshotting each in headless Chrome at exact widths of 375, 768, 1024 and 1280px, in light and dark mode. A script on each page reported any element past the right edge. The final run had no overflow on any page at any width.

**Validation:** a run with 0, negative, "nan", blank, whitespace-only or missing distance was already rejected. Added `test_editing_run_to_zero_distance_is_rejected`, which covers the edit path (0, 0.0, blank) and checks the saved distance is unchanged. Also added `test_date_fields_start_empty_and_blank_dates_do_not_filter`.

**Note on the branch:** `fix/desktop-layout` was created from `main`, which doesn't yet have Feature 6 (the search bar this fix is about). Since the branch had no commits of its own, it was moved to start from `feature/search` (`e954911`). Merge `feature/search` first, or merge this branch alone to get both.

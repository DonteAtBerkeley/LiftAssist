# Feature 5 — Stars (feature/stars)

## Prompt

Read PLAN.md, CLAUDE.md, and schema.md. This branch is Feature 5 ONLY: stars.

The stars table already exists (user_id + workout_id, unique pair). Build:
1. A star toggle (☆ / ★ in the accent color #F26B1D) on each workout card in the list and on the workout detail page. Clicking it stars or unstars the workout without losing my place.
2. A "Starred" link in the nav bar that shows only the workouts I've starred, newest first, with a friendly empty state ("No starred workouts yet — tap ☆ on a great session.").
3. Starring must be done with a POST request (not a plain link), and only for my own workouts: trying to star another user's workout returns 404. All stars live in the single stars table — one row per user per starred workout.
4. Add pytest tests: starring adds exactly one row; starring twice doesn't create a duplicate; unstarring removes the row; a user can't star another user's workout.

Save this prompt to prompts/stars.md with a short summary. Run the tests, then commit to this branch. Don't push to main. Explain in plain English what a junction table is and why stars use one table for everyone instead of one per user.

## Summary of what was built

- **`app/stars.py`** (new blueprint):
  - `POST /workouts/<id>/star` and `POST /workouts/<id>/unstar`. Both look the workout up through `_get_own_workout` (filtered by `current_user.id`), so another user's workout is a 404. Both are idempotent: starring an already-starred workout adds nothing; unstarring an unstarred one removes nothing. GET is refused (405).
  - "Without losing my place": the form sends the current page path as `next`; after the POST you're redirected back to it with `#workout-<id>`, so the browser scrolls to the same card. Only same-site paths are followed; anything else falls back to the detail page.
  - `GET /starred`: the logged-in user's starred workouts, newest workout date first, with the empty-state message.
  - `starred_ids()`: the set of workout ids the user has starred, used to draw ☆ or ★.
- **Templates**: `star_button` and `card` macros in `workouts/_macros.html`; the list, the new `workouts/starred.html`, and the detail page all use them. Cards are now an `<article>` whose title link stretches over the whole card (a form can't live inside a link), with the star button layered on top. "Starred" link added to the nav.
- **No schema change**: uses the existing `stars` table and its unique `(user_id, workout_id)` constraint; no migration.
- **Tests** (`tests/test_stars.py`): one row on star; no duplicate on double star; unstar removes the row; can't star/unstar another user's workout (404, zero rows); GET is rejected; Starred page shows only starred workouts, newest first, and the empty state; unsafe `next` is ignored.

# Feature 6 — Search, filter, and sort (feature/search)

## Prompt

Read PLAN.md, CLAUDE.md, and schema.md. This branch is Feature 6 ONLY: search, filter, and sort on the workouts list.

Build, at the top of the workouts list page:
1. Search box: matches workout title, notes, or any exercise name in the workout's sets (case-insensitive, partial matches — "squ" finds "Back Squat"). No duplicate results when a workout has several matching sets.
2. Filters: type (All / Lift / Run) and a date range (from / to).
3. Sort dropdown: Newest first (default), Oldest first, Highest effort, Longest duration.
4. Use URL query parameters (e.g. ?q=squat&type=lift&sort=effort) so the results can be bookmarked and the back button works. Keep the controls filled in with the current choices.
5. A "Clear" link that resets everything, and a friendly empty state ("No workouts match — try a different search.") when nothing matches.
6. The Starred page should support the same search and sort.
7. Compact and mobile-friendly: on small screens, filters can sit behind a "Filters" toggle.

Every query must stay filtered to the logged-in user — search must never return another user's workouts.

Add pytest tests: search by exercise name finds the right workout; type filter excludes the other type; sort by effort orders correctly; searching as User B never returns User A's workouts.

Save this prompt to prompts/search.md with a short summary. Run the tests, then commit to this branch. Don't push to main. Explain in plain English how the search turns my typed text into a database query.

## Summary of what was built

- **`app/search.py`** (new, no routes): `read_filters(request.args)` turns the query string (`q`, `type`, `from`, `to`, `sort`) into a `Filters` object. Unknown types/sorts fall back to the default, bad dates are ignored, a reversed date range is swapped, and the search text is trimmed and capped at 100 characters. `apply_filters(query, filters)` adds the WHERE clauses and ORDER BY to a query that the caller has **already** limited to `current_user.id`.
  - Search: `title ILIKE '%text%' OR notes ILIKE '%text%' OR EXISTS (a set in this workout whose exercise name ILIKE '%text%')`. Using EXISTS instead of a join means a workout with several matching sets still appears once. `%`, `_` and `\` you type are matched literally.
  - Sorts: newest (date desc), oldest (date asc), highest effort, longest duration. Workouts with no effort/duration go last; ties are broken newest first.
- **Routes**: `main.home` (`/`) and `stars.starred` (`/starred`) both read the filters and pass them through `apply_filters`. `own_workouts(filters)` in `app/workouts.py` keeps the user filter first; new `has_any_workouts()` decides between "No workouts yet" and "No workouts match".
- **Template** `workouts/_search.html`: a GET form (so every choice is in the URL and the back button works) with the search box, and a `<details>` "Filters" toggle holding Type, Sort, From, To. It's collapsed on phones and opened automatically on wider screens; it also starts open whenever a filter is set. Controls are pre-filled from the current URL. A result count and "Clear" link appear when anything differs from the default. Used by both the list and the Starred page.
- **Star button** now sends `request.full_path` as `next`, so starring from search results brings you back to the same search.
- **No schema change**, no migration.
- **Tests** (`tests/test_search.py`): exercise-name search (partial, case-insensitive, no duplicates); title and notes search; `%` treated literally; type filter; date range (including reversed and invalid); sort by effort (unrated last), oldest, duration, and unknown sort; User B's searches (list and Starred, many parameter combos) never show User A's workout; controls keep their values and "Clear" appears; empty states; Starred search and sort; starring from a search returns to that search.

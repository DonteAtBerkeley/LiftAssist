# Required test #1 — Data isolation (feature/data-isolation-test)

## Prompt

Read PLAN.md section 4 and CLAUDE.md. This branch adds required test #1: data isolation. Do not change any app code — only add the test.

Write a pytest test named test_user_b_cannot_see_user_a_workouts in tests/test_data_isolation.py that matches PLAN.md exactly:
Given User A has logged a workout titled "Leg Day", when User B logs in and opens the workouts list and tries to open Leg Day's URL directly, then User B's list is empty (does not contain "Leg Day") and the direct URL returns 404.

Go through the real app the way a user would: sign up User A through the sign-up page, create the workout through the new workout form, log out, sign up/log in as User B, then request the list page and the detail URL. Also check User B gets 404 on Leg Day's edit and delete URLs. Add clear comments explaining each step.

Save this prompt to prompts/data-isolation-test.md with a summary. Run the full test suite, then commit. Don't push to main. Explain in plain English what this test does, step by step.

## Summary of what was built

- **`tests/test_data_isolation.py`** (new): one test, `test_user_b_cannot_see_user_a_workouts`, laid out as Given / When / Then with a comment on each step. No app code was changed.
  - **Given:** User A signs up via `POST /signup` and saves "Leg Day" via the `POST /workouts/new` form. Leg Day's URL is read from the redirect. A sanity check confirms User A can see Leg Day in the list and on its page, so the test can't pass just because the workout was never saved. User A logs out (`POST /logout`).
  - **When:** User B signs up, logs out, and logs back in through `POST /login`. User B then opens the list (`/`) and requests Leg Day's detail, edit and delete URLs directly. User B also submits the edit and delete forms.
  - **Then:** User B's list returns 200, has no "Leg Day", and shows "No workouts yet.". The detail, edit and delete URLs return 404 for both GET and POST. Leg Day is still in the database with its title unchanged.
- Full suite: 243 passed.

# Faster logging (fix/faster-logging)

## Prompt

Stay on the current branch. Don't create a new one.

In my stranger test, the tester said logging a workout took too long — too many fields and too much typing, even to start. Make logging faster with the fewest taps possible, without breaking existing features or tests:

1. Only exercise and reps are required for a lift set, and only distance for a run. Date defaults to today, title auto-defaults (already built), effort defaults to 3, duration stays optional. Move notes, duration, and effort into a collapsed "More details" section.
2. Type remembers my last choice (lift or run) as the default.
3. Prefill each new set's weight and reps from the recommendation (Feature 10) when the field is empty — still never overwrite anything I typed.
4. "+ Same again" button on each set to duplicate it in one tap (most lifters do 3 identical sets).
5. "Repeat last workout" button on the workouts list that opens the new workout form prefilled with my most recent workout's exercises, sets, and type, dated today.
6. Big tap targets on phone; keep it clean on desktop.

Count the taps needed to log a 3-set bench press workout before and after this change and tell me both numbers.

Add pytest tests: a lift workout saves with only exercise + reps filled in; "Repeat last workout" only uses my own workouts; existing validation tests still pass.

Save this prompt to prompts/faster-logging.md with a summary and the before/after tap counts. Run all tests, then commit. Don't push to main.

## Summary of what was built

- **Shorter form** (`workouts/form.html`): Type (two big Lift / Run buttons) → Sets (or Distance) → Date + optional Title → a collapsed **More details** section (duration, effort, notes) → Save. More details opens by itself if something inside it has an error, so an error is never hidden.
- **Defaults** (`app/forms.py`): effort defaults to **3** on a new workout (the "—" option still clears it; editing an old workout with no effort keeps it blank). Date already defaulted to today and the title already filled itself in. A request that leaves out date/type/effort entirely falls back to today / lift / 3.
- **Only exercise + reps (lift) or distance (run) are required.** Weight is still optional. A blank weight on a *weighted* exercise still gets Feature 4's "Is this bodyweight?" question (one tap on "Save anyway"); that check was kept on purpose, and with prefill the weight is usually already filled in.
- **Type remembers your last choice**: the new form starts on the type of your most recent workout (`last_workout()` in `app/workouts.py`, filtered by `current_user.id`).
- **Recommendation prefill**: choosing an exercise you've logged before fills empty weight and reps boxes with the recommendation. A box you've typed in is never changed. Editing a workout, or a form that came back with an error or the blank-weight question, never gets prefilled. "Use this" still works.
- **"+ Same again"** on every set copies that set right below it in one tap, without opening the keyboard. Rows are renamed in on-screen order, so a set copied into the middle is saved in the middle. "+ Add set" works as before.
- **"↻ Repeat last workout"** on the workouts list (shown once you have a workout) opens `/workouts/repeat`: the new-workout form filled from your most recent workout, dated today. It copies the type, sets, a title you chose (an auto title like "Tuesday, Nov 3 — Lift" is dropped so today's is used) and a run's distance. It does not copy duration, effort or notes. Saving posts to `/workouts/new`, so it creates a new workout and the old one stays as it was. With no workouts it sends you to the empty new form.
- **Tap targets**: form controls are 3rem (48px) tall on phones, 2.75rem on desktop. Lift/Run are full-width segmented buttons, and the list's two header buttons share the row on phones.
- **Tests** (`tests/test_faster_logging.py`, 16 new): saving a lift with only exercise + reps (both as the browser sends it and with nothing else sent at all); a weighted lift with only exercise + reps (asked once, then saved); a run with only distance; reps still required; effort 3 and More details collapsed; More details opening on an error; type remembered (only from your own workouts); Repeat filling in from the most recent workout, keeping a chosen title or distance, saving as a new workout, **only ever using your own workouts** (another user's newer workout is never offered), and the button and login rules. All 243 existing tests still pass unchanged; 259 in total.

## Tap count: 3 sets of bench press at 135 lb × 8

Counted from the workouts list, for a lifter who has benched before (so a recommendation exists). Taps are touches on the screen; typing on the keyboard is listed separately.

| | Before | After |
|---|---|---|
| Steps | + New workout → tap exercise box (type "ben") → pick "Bench Press" → "Use this" → + Add set → + Add set → Save | + New workout → tap exercise box (type "ben") → pick "Bench Press" (weight and reps fill themselves) → + Same again → + Same again → Save |
| **Taps** | **7** | **6** |
| With "Repeat last workout" (last session was this bench workout) | not available | **2** (Repeat last workout → Save) |

Notes:
- Before, "+ Add set" put the cursor in the new reps box, which opens the phone keyboard. That can cover the next button and cost an extra tap to close it. "+ Same again" doesn't open the keyboard.
- The bigger change is what you have to look at: before, you had to scroll past type, date, title, duration and effort to reach the sets, and notes came after them. Now you see type, the sets, then date and title, and everything else is tucked away.
- First-ever bench session (no recommendation yet): 8 taps before and after, plus typing the weight and reps. Repeat or the recommendation help from the second session on.

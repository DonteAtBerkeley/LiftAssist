"""Built-in exercise catalog: common movements offered in the exercise dropdown.

This is code, not user data. Nothing here is written to the database until a
user logs a set of one of these exercises; then a row is created in *their*
`exercises` table, with `is_bodyweight` copied from here.

Each entry is (name, kind) where kind is "weighted" or "bodyweight".
Names are matched ignoring case and extra spaces ("bench press" = "Bench Press").
"""

WEIGHTED = "weighted"
BODYWEIGHT = "bodyweight"

CATALOG = [
    # Legs
    ("Back Squat", WEIGHTED),
    ("Front Squat", WEIGHTED),
    ("Goblet Squat", WEIGHTED),
    ("Box Squat", WEIGHTED),
    ("Overhead Squat", WEIGHTED),
    ("Hack Squat", WEIGHTED),
    ("Leg Press", WEIGHTED),
    ("Bulgarian Split Squat", WEIGHTED),
    ("Dumbbell Lunge", WEIGHTED),
    ("Barbell Lunge", WEIGHTED),
    ("Leg Extension", WEIGHTED),
    ("Leg Curl", WEIGHTED),
    ("Standing Calf Raise", WEIGHTED),
    ("Seated Calf Raise", WEIGHTED),
    ("Hip Thrust", WEIGHTED),
    ("Hip Abduction", WEIGHTED),
    ("Hip Adduction", WEIGHTED),
    ("Air Squat", BODYWEIGHT),
    ("Jump Squat", BODYWEIGHT),
    ("Pistol Squat", BODYWEIGHT),
    ("Lunge", BODYWEIGHT),
    ("Walking Lunge", BODYWEIGHT),
    ("Step-Up", BODYWEIGHT),
    ("Glute Bridge", BODYWEIGHT),
    ("Calf Raise", BODYWEIGHT),
    ("Wall Sit", BODYWEIGHT),
    ("Nordic Curl", BODYWEIGHT),
    ("Box Jump", BODYWEIGHT),
    # Hinge / posterior chain
    ("Deadlift", WEIGHTED),
    ("Romanian Deadlift", WEIGHTED),
    ("Sumo Deadlift", WEIGHTED),
    ("Trap Bar Deadlift", WEIGHTED),
    ("Stiff-Leg Deadlift", WEIGHTED),
    ("Good Morning", WEIGHTED),
    ("Kettlebell Swing", WEIGHTED),
    ("Back Extension", BODYWEIGHT),
    ("Superman", BODYWEIGHT),
    # Chest
    ("Bench Press", WEIGHTED),
    ("Incline Bench Press", WEIGHTED),
    ("Decline Bench Press", WEIGHTED),
    ("Close-Grip Bench Press", WEIGHTED),
    ("Dumbbell Bench Press", WEIGHTED),
    ("Incline Dumbbell Press", WEIGHTED),
    ("Dumbbell Fly", WEIGHTED),
    ("Cable Fly", WEIGHTED),
    ("Machine Chest Press", WEIGHTED),
    ("Pec Deck", WEIGHTED),
    ("Weighted Dip", WEIGHTED),
    ("Push-Up", BODYWEIGHT),
    ("Diamond Push-Up", BODYWEIGHT),
    ("Decline Push-Up", BODYWEIGHT),
    ("Dip", BODYWEIGHT),
    # Shoulders
    ("Overhead Press", WEIGHTED),
    ("Push Press", WEIGHTED),
    ("Seated Dumbbell Press", WEIGHTED),
    ("Arnold Press", WEIGHTED),
    ("Landmine Press", WEIGHTED),
    ("Lateral Raise", WEIGHTED),
    ("Front Raise", WEIGHTED),
    ("Rear Delt Fly", WEIGHTED),
    ("Face Pull", WEIGHTED),
    ("Upright Row", WEIGHTED),
    ("Shrug", WEIGHTED),
    ("Pike Push-Up", BODYWEIGHT),
    ("Handstand Push-Up", BODYWEIGHT),
    # Back
    ("Barbell Row", WEIGHTED),
    ("Pendlay Row", WEIGHTED),
    ("Dumbbell Row", WEIGHTED),
    ("Seated Cable Row", WEIGHTED),
    ("T-Bar Row", WEIGHTED),
    ("Lat Pulldown", WEIGHTED),
    ("Straight-Arm Pulldown", WEIGHTED),
    ("Weighted Pull-Up", WEIGHTED),
    ("Pull-Up", BODYWEIGHT),
    ("Chin-Up", BODYWEIGHT),
    ("Inverted Row", BODYWEIGHT),
    ("Muscle-Up", BODYWEIGHT),
    # Arms
    ("Barbell Curl", WEIGHTED),
    ("Dumbbell Curl", WEIGHTED),
    ("Hammer Curl", WEIGHTED),
    ("Preacher Curl", WEIGHTED),
    ("Cable Curl", WEIGHTED),
    ("Tricep Pushdown", WEIGHTED),
    ("Skull Crusher", WEIGHTED),
    ("Overhead Tricep Extension", WEIGHTED),
    ("Bench Dip", BODYWEIGHT),
    # Olympic / full body
    ("Hang Clean", WEIGHTED),
    ("Power Clean", WEIGHTED),
    ("Clean and Jerk", WEIGHTED),
    ("Snatch", WEIGHTED),
    ("Hang Snatch", WEIGHTED),
    ("Thruster", WEIGHTED),
    ("Turkish Get-Up", WEIGHTED),
    ("Farmer's Carry", WEIGHTED),
    ("Sled Push", WEIGHTED),
    ("Burpee", BODYWEIGHT),
    ("Mountain Climber", BODYWEIGHT),
    ("Jumping Jack", BODYWEIGHT),
    ("Bear Crawl", BODYWEIGHT),
    ("High Knees", BODYWEIGHT),
    # Core
    ("Cable Crunch", WEIGHTED),
    ("Crunch", BODYWEIGHT),
    ("Sit-Up", BODYWEIGHT),
    ("Bicycle Crunch", BODYWEIGHT),
    ("Plank", BODYWEIGHT),
    ("Side Plank", BODYWEIGHT),
    ("Hanging Leg Raise", BODYWEIGHT),
    ("Lying Leg Raise", BODYWEIGHT),
    ("Russian Twist", BODYWEIGHT),
    ("Ab Wheel Rollout", BODYWEIGHT),
    ("V-Up", BODYWEIGHT),
    ("Dead Bug", BODYWEIGHT),
    ("Bird Dog", BODYWEIGHT),
    ("Hollow Hold", BODYWEIGHT),
    ("L-Sit", BODYWEIGHT),
    ("Flutter Kick", BODYWEIGHT),
]


def normalize(name):
    """The matching key for an exercise name: trimmed, single-spaced, lowercase."""
    return " ".join((name or "").split()).lower()


# normalized name -> (catalog name, is_bodyweight)
_BY_KEY = {normalize(name): (name, kind == BODYWEIGHT) for name, kind in CATALOG}


def lookup(name):
    """(catalog name, is_bodyweight) for a catalog exercise, or None for a custom name."""
    return _BY_KEY.get(normalize(name))
